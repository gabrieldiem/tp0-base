import socket
from logging import Logger
from socket import socket as Socket
from typing import Optional

class Server:
    """
    TCP echo server running in a separate process.

    The server listens for incoming connections, receives messages
    terminated by a newline, logs them, and echoes them back to the client.
    """
    RAW_MESSAGE_DELIMITER = b"\n"
    SOCKET_BUFFER_SIZE = 1024
    CHAR_ENCODING = "utf-8"

    def __init__(self, port: int, listen_backlog: int, logger: Logger):
        """
        Initialize the server socket and prepare it to accept connections.

        Parameters
        ----------
        port : int
            Port number to bind the server to.
        listen_backlog : int
            Maximum number of queued connections.
        lock : LockType
            Multiprocessing lock to synchronize socket operations.
        logger : Logger
            Logger instance for recording server events.
        """
        super().__init__()
        self._port: int = port
        self._listen_backlog: int = listen_backlog

        self._server_socket: Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(("", self._port))
        self._server_socket.listen(self._listen_backlog)

        self._logger: Logger = logger
        self._running: bool = False
        self._stopped: bool = False

    def run(self) -> None:
        """
        Main server loop.

        Accepts new client connections and handles them one at a time.
        Stops when the listening socket is closed.
        """
        self._running = True
        self._logger.info(f"action: starting_loop | result: success")

        if self._stopped:
            return

        while self._running:
            client_sock: Optional[Socket] = self.__accept_new_connection()
            
            if not client_sock:
                break
            
            self.__handle_client_connection(client_sock)

    def __handle_client_connection(self, client_sock: Socket) -> None:
        """
        Handle a single client connection.

        Reads a message, logs it, echoes it back, and closes the socket.
        """
        try:
            addr = client_sock.getpeername()

            msg: str = self.__receive_message(client_sock)
            self._logger.info(
                f"action: receive_message | result: success | ip: {addr[0]} | msg: {msg}"
            )

            if self._running:
                self.__send_message(client_sock, msg)

        except OSError as e:
            self._logger.error("action: receive_message | result: fail | error: {e}")

        finally:
            self.__shutdown_socket(client_sock)
            self._logger.info(
                "action: client_connection_socket_closed  | result: success"
            )

    def __receive_message(self, client_sock: Socket) -> str:
        """
        Receive a message from the client until a newline delimiter is found.

        Raises
        ------
        ConnectionError
            If the client disconnects before sending a complete message.
        """
        data: bytes = b""
        delimiter: bytes = self.RAW_MESSAGE_DELIMITER

        while delimiter not in data and self._running:
            chunk: bytes = client_sock.recv(self.SOCKET_BUFFER_SIZE)

            if not chunk:
                raise ConnectionError("Client disconnected during reception")

            data += chunk

        return data.strip().decode(self.CHAR_ENCODING)

    def __send_message(self, client_sock: Socket, msg: str) -> None:
        """
        Send a message back to the client, appending a newline delimiter.
        """
        raw_encoded_msg: bytes = f"{msg}\n".encode(self.CHAR_ENCODING)
        client_sock.sendall(raw_encoded_msg)

    def __accept_new_connection(self) -> Optional[Socket]:
        """
        Block until a new client connects, then return the client socket.
        """
        self._logger.info("action: accept_connections | result: in_progress")
        
        try:
            client_socket, addr = self._server_socket.accept()
            self._logger.info(
                f"action: accept_connections | result: success | ip: {addr[0]}"
            )
            return client_socket
        except OSError:
            # Socket was closed -> shutdown
            self._logger.info(
                f"action: server_welcomming_socket_shutdown | result: success"
            )
        
        return None

    def __shutdown_socket(self, a_socket: Socket):
        a_socket.shutdown(socket.SHUT_RDWR)
        a_socket.close()

    def stop(self) -> None:
        """
        Stop the server by shutting down and closing the listening socket.

        Safe to call multiple times; subsequent calls have no effect.
        """
        if self._stopped:
            return

        self.__shutdown_socket(self._server_socket)
        self._logger.info("action: server_welcomming_socket_closed  | result: success")

        self._stopped = True
        self._running = False
