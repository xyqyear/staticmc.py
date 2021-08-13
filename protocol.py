import enum

from buffer import BufferedProtocolReader


class ProtocolState(enum.Enum):
    HANDSHAKE = 0
    STATUS = 1
    LOGIN = 2
    PLAY = 3


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
