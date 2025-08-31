import socket
from multiprocessing import Process
from logging import Logger
from socket import socket as Socket
from common.exceptions.socket_not_initialized_exception import (
    SocketNotInitializedException,
)

from typing import Optional, List


class Server(Process):
    RAW_MESSAGE_DELIMITER = b"\n"
    SOCKET_BUFFER_SIZE = 1024
    CHAR_ENCODING = "utf-8"

    def __init__(self, port: str, listen_backlog: int, logger: Logger):
        super().__init__()
        self._port: str = port
        self._listen_backlog: int = listen_backlog
        self._server_socket: Optional[Socket] = None
        self._logger: Logger = logger

    def run(self) -> None:
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(("", self._port))
        self._server_socket.listen(self._listen_backlog)

        self._logger.info(f"action: starting_loop | result: success")

        while True:
            try:
                client_sock: Socket = self.__accept_new_connection()
            except OSError:
                # Socket was closed -> shutdown
                break
            except SocketNotInitializedException as e:
                self._logger.critical(
                    f"action: accept_connections | result: fail | {e}"
                )
                break

            self.__handle_client_connection(client_sock)

    def __handle_client_connection(self, client_sock: Socket) -> None:
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            addr = client_sock.getpeername()

            msg: str = self.__receive_message(client_sock)
            self._logger.info(
                f"action: receive_message | result: success | ip: {addr[0]} | msg: {msg}"
            )

            self.__send_message(client_sock, msg)

        except OSError as e:
            self._logger.error("action: receive_message | result: fail | error: {e}")

        finally:
            client_sock.close()
            self._logger.info("action: client_connection_socket_closed  | result: success")

    def __receive_message(self, client_sock: Socket) -> str:
        data: bytes = b""
        delimiter: bytes = self.RAW_MESSAGE_DELIMITER

        while delimiter not in data:
            chunk: bytes = client_sock.recv(self.SOCKET_BUFFER_SIZE)

            if not chunk:
                raise ConnectionError("Client disconnected during reception")

            data += chunk

        return data.strip().decode(self.CHAR_ENCODING)

    def __send_message(self, client_sock: Socket, msg: str) -> None:
        raw_encoded_msg: bytes = f"{msg}\n".encode(self.CHAR_ENCODING)
        client_sock.sendall(raw_encoded_msg)

    def __accept_new_connection(self) -> Socket:
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        if self._server_socket:
            self._logger.info("action: accept_connections | result: in_progress")
            c, addr = self._server_socket.accept()
            self._logger.info(
                f"action: accept_connections | result: success | ip: {addr[0]}"
            )
            return c

        raise SocketNotInitializedException

    def stop(self) -> None:
        """Stop the server loop"""
        if self._server_socket:
            try:
                self._server_socket.close()
                self._logger.info("action: server_welcomming_socket_closed  | result: success")
            except OSError:
                pass
