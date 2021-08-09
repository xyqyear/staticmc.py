import threading
import logging
import socket
import struct
import time
import enum
import io

from typing import Tuple

SERVER_ADDRESS = ("0.0.0.0", 25565)


class MCServer(threading.Thread):
    def __init__(self):
        super().__init__()

    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(SERVER_ADDRESS)
        s.listen(10)
        while True:
            sock, peer_addr = s.accept()
            t = MCServerThread(sock, peer_addr)
            t.start()


class ProtocolState(enum.Enum):
    HANDSHAKE = enum.auto()
    STATUS = enum.auto()
    LOGIN = enum.auto()
    PLAY = enum.auto()


class MCServerThread(threading.Thread):
    def __init__(self,
                 sock: socket.socket,
                 peer_addr: Tuple[str, int],
                 use_compression=False):
        self.sock = sock
        self.peer_addr = peer_addr
        self.use_compression = use_compression
        self.state = ProtocolState.HANDSHAKE
        super().__init__()

    def run(self):
        print(f"{self.peer_addr} connected.")
        reader = ProtocolReader(self.sock)


class ProtocolReader:
    def __init__(self, stream: socket.socket):
        self.stream = stream

    def _read(self, length):
        return self.stream.recv(length)

    def _unpack(self, fmt, data_length):
        return struct.unpack(fmt, self._read(data_length))

    def read(self, length):
        return self._read(length)

    def _read_varnum(self, max_offset, max_bits):
        total = 0
        shift = 0
        val = 0x80
        while val & 0x80:
            if shift == max_offset:
                raise Exception
            val = self._unpack("B", 1)[0]
            total |= ((val & 0x7F) << shift)
            shift += 7
        if total & (1 << (max_bits - 1)):
            total = total - (1 << max_bits)
        return total

    def read_varint(self, max_offset):
        return self._read_varnum(35, 32)

    def read_varlong(self, max_offset):
        total = self._read_varnum(70, 64)
