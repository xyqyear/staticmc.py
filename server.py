import asyncio
from protocol import HandshakePacket, ProtocolState
from buffer import BufferedProtocolReader, ProtocolReader


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
