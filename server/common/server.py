from logging import Logger
from common.protocol import Protocol
from common.socket import Socket
from typing import Tuple
from common.utils import Bet, store_bets

from common.messages import (
    Message,
    MsgRegisterBet,
    UNKNOWN_BET_INFO,
    FAILURE_UNKNOWN_MESSAGE,
)


class Server:
    """
    TCP bet registration server.

    The server listens on a given port, accepts client connections,
    and processes messages defined by the custom binary protocol.
    It specifically handles bet registration requests (`MsgRegisterBet`),
    converts them into domain `Bet` objects, stores them, and responds
    with either a success (`MsgRegisterBetOk`) or failure
    (`MsgRegisterBetFailed`) message.

    The server runs in a loop until explicitly stopped, ensuring
    clean shutdown of sockets and proper logging of all events.
    """

    def __init__(self, port: int, listen_backlog: int, logger: Logger):
        """
        Initialize the server with a listening socket and logger.

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
        one at a time. For each connection, the server receives a
        protocol message, processes it, and sends an appropriate
        response. The loop stops when the server is explicitly
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

        Reads a message from the client, logs it, and dispatches it
        to the appropriate handler. If the message is a valid
        `MsgRegisterBet`, it is converted into a `Bet` and stored.
        Otherwise, a failure response is sent.

        Parameters
        ----------
        client_sock : Socket
            The client socket for communication.
        client_addr : Tuple[str, int]
            The client address (IP, port).
        """
        try:
            msg: Message = self._protocol.receive_message(client_sock)
            self._logger.info(
                f"action: receive_message | result: success | ip: {client_addr[0]} | msg: {msg}"
            )

            if self._running:
                self.send_message_response(client_sock, msg)

        except (ConnectionError, ValueError, OSError) as e:
            self._logger.error(f"action: receive_message | result: fail | error: {e}")

        finally:
            self._protocol.shutdown_socket(client_sock)

    def send_message_response(self, client_sock: Socket, msg: Message) -> None:
        """
        Process a received message and send an appropriate response.

        If the message is a `MsgRegisterBet`, it is converted into a
        `Bet` object, stored, and acknowledged with a
        `MsgRegisterBetOk`. If the message type is unknown, a
        `MsgRegisterBetFailed` is sent instead.

        Parameters
        ----------
        client_sock : Socket
            The client socket to send the response to.
        msg : Message
            The received protocol message.
        """
        if isinstance(msg, MsgRegisterBet):
            message: MsgRegisterBet = msg
            bet: Bet = message.get_bet()

            store_bets([bet])

            self._protocol.send_register_bet_ok(
                client_sock, message._dni, message._number
            )

            self._logger.info(
                f"action: apuesta_almacenada | result: success | dni: {bet.document} | numero: {bet.number}"
            )

        else:
            self._protocol.send_register_bet_failed(
                client_sock, UNKNOWN_BET_INFO, UNKNOWN_BET_INFO, FAILURE_UNKNOWN_MESSAGE
            )

            self._logger.error(f"action: mensaje_desconocido | result: fail")

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
