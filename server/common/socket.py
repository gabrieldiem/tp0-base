import socket
from socket import socket as StdSocket
from typing import Tuple
from common.messages import (
    Message,
    MSG_TYPE_REGISTER_BET,
    MSG_TYPE_REGISTER_BET_OK,
    MSG_TYPE_REGISTER_BET_FAILED,
    MsgRegisterBet,
    MsgRegisterBetOk,
    MsgRegisterBetFailed,
    SIZEOF_UINT16,
    SIZEOF_UINT32,
    SIZEOF_UINT64,
    SIZEOF_INT64,
)


class Socket:
    NETWORK_ENDIANNESS = "big"
    CHAR_ENCODING = "utf-8"

    def __init__(self, port: int, listen_backlog: int):
        """Create a listening TCP socket bound to the given port."""
        self._socket: StdSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(("", port))
        self._socket.listen(listen_backlog)

    @classmethod
    def from_existing(cls, sock: StdSocket) -> "Socket":
        """Wrap an existing socket in a Socket instance."""
        obj: Socket = cls.__new__(cls)  # bypass __init__
        obj._socket = sock
        return obj

    def shutdown(self):
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()

    def accept(self) -> Tuple[Tuple[str, int], "Socket"]:
        """Accept a new connection and return (addr, Socket)."""
        client_socket, addr = self._socket.accept()
        return addr, Socket.from_existing(client_socket)

    def send_message(self, msg: Message) -> None:
        raw_message: bytes = msg.to_bytes(
            Socket.CHAR_ENCODING, Socket.NETWORK_ENDIANNESS
        )
        self._socket.sendall(raw_message)

    def receive_message(self) -> Message:
        return self.__decode_message()

    def __decode_message(self) -> Message:
        # Read header
        sizeof_header: int = SIZEOF_UINT16 + SIZEOF_UINT64
        header: bytes = self._socket.recv(sizeof_header)
        if len(header) < sizeof_header:
            raise ConnectionError("Incomplete header")

        msg_type: int = int.from_bytes(
            header[0:SIZEOF_UINT16], Socket.NETWORK_ENDIANNESS
        )
        length: int = int.from_bytes(
            header[SIZEOF_UINT16:sizeof_header], Socket.NETWORK_ENDIANNESS
        )

        # Read payload
        payload: bytes = b""
        while len(payload) < length:
            chunk = self._socket.recv(length - len(payload))
            if not chunk:
                raise ConnectionError("Client disconnected")
            payload += chunk

        # Dispatch
        if msg_type == MSG_TYPE_REGISTER_BET:
            return self.__decode_register_bet(payload)
        elif msg_type == MSG_TYPE_REGISTER_BET_OK:
            return self.__decode_register_bet_ok(payload)
        elif msg_type == MSG_TYPE_REGISTER_BET_FAILED:
            return self.__decode_register_bet_failed(payload)
        else:
            raise ValueError(f"Unknown msg_type {msg_type}")

    def __decode_register_bet(self, payload: bytes) -> MsgRegisterBet:
        offset: int = 0

        # Agency
        agency: int = int.from_bytes(
            payload[offset : offset + SIZEOF_UINT32], Socket.NETWORK_ENDIANNESS
        )
        offset += SIZEOF_UINT32

        # Name
        name_len: int = int.from_bytes(
            payload[offset : offset + SIZEOF_UINT32], Socket.NETWORK_ENDIANNESS
        )
        offset += SIZEOF_UINT32
        name: str = payload[offset : offset + name_len].decode("utf-8")
        offset += name_len

        # Surname
        surname_len: int = int.from_bytes(
            payload[offset : offset + SIZEOF_UINT32], Socket.NETWORK_ENDIANNESS
        )
        offset += SIZEOF_UINT32
        surname: str = payload[offset : offset + surname_len].decode("utf-8")
        offset += surname_len

        # Dni
        dni: int = int.from_bytes(
            payload[offset : offset + SIZEOF_UINT32], Socket.NETWORK_ENDIANNESS
        )
        offset += SIZEOF_UINT32

        # Birthdate
        birthdate: int = int.from_bytes(
            payload[offset : offset + SIZEOF_INT64],
            Socket.NETWORK_ENDIANNESS,
            signed=True,
        )
        offset += SIZEOF_INT64

        # Number
        number: int = int.from_bytes(
            payload[offset : offset + SIZEOF_UINT32], Socket.NETWORK_ENDIANNESS
        )
        offset += SIZEOF_UINT32

        return MsgRegisterBet(agency, name, surname, dni, birthdate, number)

    def __decode_register_bet_ok(self, payload: bytes) -> MsgRegisterBetOk:
        offset: int = 0
        dni: int = int.from_bytes(
            payload[offset : offset + SIZEOF_UINT32], Socket.NETWORK_ENDIANNESS
        )
        offset += SIZEOF_UINT32

        number: int = int.from_bytes(
            payload[offset : offset + SIZEOF_UINT32], Socket.NETWORK_ENDIANNESS
        )
        offset += SIZEOF_UINT32

        return MsgRegisterBetOk(dni, number)

    def __decode_register_bet_failed(self, payload: bytes) -> MsgRegisterBetFailed:
        offset = 0
        dni: int = int.from_bytes(
            payload[offset : offset + SIZEOF_UINT32], Socket.NETWORK_ENDIANNESS
        )
        offset += SIZEOF_UINT32

        number: int = int.from_bytes(
            payload[offset : offset + SIZEOF_UINT32], Socket.NETWORK_ENDIANNESS
        )
        offset += SIZEOF_UINT32

        error_code: int = int.from_bytes(
            payload[offset : offset + SIZEOF_UINT16], Socket.NETWORK_ENDIANNESS
        )
        offset += SIZEOF_UINT16

        return MsgRegisterBetFailed(dni, number, error_code)
