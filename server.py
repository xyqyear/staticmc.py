import asyncio
import struct
import enum
import io


class ProtocolState(enum.Enum):
    HANDSHAKE = 0
    STATUS = 1
    LOGIN = 2
    PLAY = 3


class ProtocolReader:
    def __init__(self, reader: asyncio.StreamReader) -> None:
        self.reader = reader

    async def _read(self, length: int) -> bytes:
        return await self.reader.read(length)

    async def _unpack(self, fmt: str, data_length: int):
        return struct.unpack(fmt, await self._read(data_length))

    async def read(self, length: int) -> bytes:
        return await self._read(length)

    async def _read_varnum(self, max_offset: int, max_bits: int) -> int:
        total = 0
        shift = 0
        val = 0x80
        while val & 0x80:
            if shift == max_offset:
                raise Exception
            val = (await self._unpack("B", 1))[0]
            total |= (val & 0x7F) << shift
            shift += 7
        if total & (1 << (max_bits - 1)):
            total = total - (1 << max_bits)
        return total

    async def read_varint(self) -> int:
        return await self._read_varnum(35, 32)

    async def read_varlong(self) -> int:
        return await self._read_varnum(70, 64)


class BufferedProtocolReader:
    def __init__(self, data: bytes = b""):
        self.buffer = io.BytesIO(data)

    def fill(self, data: bytes):
        self.buffer = io.BytesIO(data)

    def _read(self, length: int):
        return self.buffer.read(length)

    def _unpack(self, fmt: str):
        return struct.unpack(fmt, self.read(struct.calcsize(fmt)))

    def read(self, length: int):
        return self._read(length)

    def _read_varnum(self, max_offset: int, max_bits: int) -> int:
        total = 0
        shift = 0
        val = 0x80
        while val & 0x80:
            if shift == max_offset:
                raise Exception
            val = self._unpack("B")[0]
            total |= (val & 0x7F) << shift
            shift += 7
        if total & (1 << (max_bits - 1)):
            total = total - (1 << max_bits)
        return total

    def read_varint(self) -> int:
        return self._read_varnum(35, 32)

    def read_varlong(self) -> int:
        return self._read_varnum(70, 64)

    def read_string(self) -> str:
        length = self.read_varint()
        return self.read(length).decode("utf-8")

    def read_uint16(self) -> int:
        return self._unpack(">H")[0]


class HandshakePacket:
    def __init__(
        self,
        protocol_version: int,
        server_address: str,
        server_port: int,
        next_state: ProtocolState,
    ) -> None:
        self.protocol_version = protocol_version
        self.server_address = server_address
        self.server_port = server_port
        self.next_state = next_state

    @classmethod
    def from_bytes_io(cls, buffer: BufferedProtocolReader):
        protocol_version = buffer.read_varint()
        server_address = buffer.read_string()
        server_port = buffer.read_uint16()
        next_state_int = buffer.read_varint()
        next_state: ProtocolState
        if next_state_int == 1:
            next_state = ProtocolState.STATUS
        elif next_state_int == 2:
            next_state = ProtocolState.LOGIN
        else:
            raise Exception("unexpected next state")
        return cls(protocol_version, server_address, server_port, next_state)


class Server:
    def __init__(self, host: str = "0.0.0.0", port: int = 25565) -> None:
        self.host = host
        self.port = port

    async def start(self):
        server = await asyncio.start_server(
            self.handle_connection, self.host, self.port
        )

        async with server:
            await server.serve_forever()

    async def handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        connection_handler = ConnectionHandler(reader, writer)
        asyncio.get_event_loop().create_task(connection_handler.start())


class ConnectionHandler:
    def __init__(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self.reader = reader
        self.writer = writer

    async def start(self):
        protocol_reader = ProtocolReader(self.reader)
        worker = Worker(self.writer)

        while True:
            packet_length = await protocol_reader.read_varint()
            packet_content = await protocol_reader.read(packet_length)
            await worker.dispatch(packet_content)


class Worker:
    def __init__(self, writer: asyncio.StreamWriter) -> None:
        self.writer = writer
        self.protocol_state = ProtocolState.HANDSHAKE
        self.buffered_reader = BufferedProtocolReader()
        self.handler = {ProtocolState.HANDSHAKE: {0: self.handle_handshake}}

    async def send(self, data: bytes):
        self.writer.write(data)
        await self.writer.drain()

    async def dispatch(self, packet_content: bytes) -> None:
        """
        packet_content: raw packet content, including packet_id
        """
        self.buffered_reader.fill(packet_content)
        packet_id = self.buffered_reader.read_varint()
        await self.handler[self.protocol_state][packet_id](self.buffered_reader)

    async def handle_handshake(self, buffer: BufferedProtocolReader):
        packet = HandshakePacket.from_bytes_io(buffer)
        self.protocol_state = packet.next_state
