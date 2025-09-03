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
    """
    Protocol-aware TCP socket wrapper.

    This class abstracts away raw socket operations and provides
    higher-level methods for sending and receiving protocol messages.

    Attributes
    ----------
    NETWORK_ENDIANNESS : str
        Byte order used for encoding integers ("big" for network order).
    CHAR_ENCODING : str
        Character encoding used for string fields ("utf-8").
    _socket : socket.socket
        The underlying Python socket object.
    """

    NETWORK_ENDIANNESS = "big"
    CHAR_ENCODING = "utf-8"

    def __init__(self, port: int, listen_backlog: int):
        """
        Create a listening TCP socket bound to the given port.

        Parameters
        ----------
        port : int
            Port number to bind the server socket to.
        listen_backlog : int
            Maximum number of queued connections.
        """
        self._socket: StdSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(("", port))
        self._socket.listen(listen_backlog)

    @classmethod
    def __from_existing(cls, sock: StdSocket) -> "Socket":
        """
        Wrap an existing raw socket in a Socket instance.

        Used when accepting new client connections.

        Parameters
        ----------
        sock : socket.socket
            An existing Python socket object.

        Returns
        -------
        Socket
            A protocol-aware `Socket` wrapper.
        """
        obj: Socket = cls.__new__(cls)  # bypass __init__
        obj._socket = sock
        return obj

    def shutdown(self):
        """
        Shut down and close the socket.

        Closes both directions of communication and releases resources.
        """
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()

    def accept(self) -> Tuple[Tuple[str, int], "Socket"]:
        """
        Accept a new client connection.

        Returns
        -------
        Tuple[Tuple[str, int], Socket]
            A tuple containing the client address (IP, port) and a
            wrapped `Socket` instance for the client connection.
        """
        client_socket, addr = self._socket.accept()
        return addr, Socket.__from_existing(client_socket)

    def send_message(self, msg: Message) -> None:
        """
        Send a protocol message to the connected peer.

        Parameters
        ----------
        msg : Message
            The message to send. It will be serialized using
            `Message.to_bytes()`.
        """
        raw_message: bytes = msg.to_bytes(
            Socket.CHAR_ENCODING, Socket.NETWORK_ENDIANNESS
        )
        self._socket.sendall(raw_message)

    def receive_message(self) -> Message:
        """
        Receive a protocol message from the connected peer.

        Reads the message header and payload, then decodes it into
        the appropriate `Message` subclass.

        Returns
        -------
        Message
            The decoded message object.
        """
        return self.__decode_message()

    def __decode_message(self) -> Message:
        """
        Decode a single message from the socket.

        Reads the header (msg_type + payload length), then reads the
        payload and dispatches to the appropriate decoder.

        Returns
        -------
        Message
            A decoded `Message` subclass instance.

        Raises
        ------
        ConnectionError
            If the client disconnects before the full message is read.
        ValueError
            If the message type is unknown.
        """
        sizeof_header: int = SIZEOF_UINT16 + SIZEOF_UINT64
        header: bytes = self.__receive_all(sizeof_header)

        msg_type: int = int.from_bytes(
            header[0:SIZEOF_UINT16], Socket.NETWORK_ENDIANNESS
        )
        length: int = int.from_bytes(
            header[SIZEOF_UINT16:sizeof_header], Socket.NETWORK_ENDIANNESS
        )

        payload: bytes = self.__receive_all(length)

        # Dispatch
        if msg_type == MSG_TYPE_REGISTER_BET:
            return self.__decode_register_bet(payload)
        elif msg_type == MSG_TYPE_REGISTER_BET_OK:
            return self.__decode_register_bet_ok(payload)
        elif msg_type == MSG_TYPE_REGISTER_BET_FAILED:
            return self.__decode_register_bet_failed(payload)
        else:
            raise ValueError(f"Unknown msg_type {msg_type}")

    def __receive_all(self, n_bytes: int) -> bytes:
        """
        Read exactly `n_bytes` from the socket.

        Keeps calling `recv()` until the requested number of bytes
        is read, or raises an error if the client disconnects.

        Parameters
        ----------
        n_bytes : int
            Number of bytes to read.

        Returns
        -------
        bytes
            The received data.

        Raises
        ------
        ConnectionError
            If the client disconnects before all bytes are read.
        """
        data: bytes = b""
        while len(data) < n_bytes:
            chunk = self._socket.recv(n_bytes - len(data))
            if not chunk:
                raise ConnectionError(
                    "Client disconnected during byte reading from socket"
                )
            data += chunk
        return data

    def __decode_register_bet(self, payload: bytes) -> MsgRegisterBet:
        """
        Decode a `MsgRegisterBet` message from its payload.

        Payload format:
            [4 bytes agency]
            [4 bytes name_length][name_bytes]
            [4 bytes surname_length][surname_bytes]
            [4 bytes dni]
            [8 bytes birthdate_unix_timestamp]
            [4 bytes number]

        Returns
        -------
        MsgRegisterBet
        """
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
        """
        Decode a `MsgRegisterBetOk` message from its payload.

        Payload format:
            [4 bytes dni]
            [4 bytes number]

        Returns
        -------
        MsgRegisterBetOk
        """
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
        """
        Decode a `MsgRegisterBetFailed` message from its payload.

        Payload format:
            [4 bytes dni]
            [4 bytes number]
            [2 bytes error_code]

        Returns
        -------
        MsgRegisterBetFailed
        """
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
