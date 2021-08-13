import asyncio
import struct
import io


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
