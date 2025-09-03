from logging import Logger
from common.protocol import Protocol
from common.socket import Socket
from typing import Tuple

from common.messages import Message, MsgRegisterBet


class Server:
    """
    TCP echo server.

    The server listens on a given port, accepts client connections,
    receives newline-terminated messages, logs them, and echoes them
    back to the client. It runs in a loop until explicitly stopped,
    ensuring clean shutdown of sockets and proper logging of events.
    """

    def __init__(self, port: int, listen_backlog: int, logger: Logger):
        """
        Initialize the server socket and prepare it to accept connections.

        Parameters
        ----------
        port : int
            Port number to bind the server to.
        listen_backlog : int
            Maximum number of queued connections.
        logger : Logger
            Logger instance for recording server events.
        """
        self._protocol = Protocol(port, listen_backlog, logger)
        self._logger: Logger = logger
        self._running: bool = False
        self._stopped: bool = False

    def run(self) -> None:
        """
        Start the main server loop.

        Continuously accepts new client connections and handles them
        one at a time. The loop stops when the server is explicitly
        stopped or the listening socket is closed.
        """
        self._running = True
        self._logger.info(f"action: starting_loop | result: success")

        if self._stopped:
            return

        while self._running:
            addr, client_sock = self._protocol.accept_new_connection()

            if not client_sock:
                break

            self.__handle_client_connection(client_sock, addr)

    def __handle_client_connection(
        self, client_sock: Socket, client_addr: Tuple[str, int]
    ) -> None:
        """
        Handle a single client connection.

        Reads a message from the client, logs it, echoes it back,
        and then closes the connection. Errors are logged and exceptions are handled.
        """
        try:
            msg: Message = self._protocol.receive_message(client_sock)
            self._logger.info(
                f"action: receive_message | result: success | ip: {client_addr[0]} | msg: {msg}"
            )

            if self._running:
                self.send_message_response(client_sock, msg)

        except OSError as e:
            self._logger.error(f"action: receive_message | result: fail | error: {e}")

        finally:
            self._protocol.shutdown_socket(client_sock)

    def send_message_response(self, client_sock: Socket, msg: Message) -> None:
        """
        Send a message back to the client.

        The message is encoded as UTF-8 and terminated with a newline
        before being sent.
        """
        if isinstance(msg, MsgRegisterBet):
            message: MsgRegisterBet = msg
            self._protocol.send_register_bet_ok(
                client_sock, message.dni, message.number
            )
        else:
            self._protocol.send_register_bet_failed(client_sock)

    def stop(self) -> None:
        """
        Stop the server.

        Shuts down and closes the listening socket, sets the server
        state to stopped, and prevents further connections.
        """
        if self._stopped:
            return

        self._protocol.shutdown()
        self._stopped = True
        self._running = False
