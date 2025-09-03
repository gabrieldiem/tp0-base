from common.socket import Socket
from logging import Logger
from typing import Optional, Tuple
from common.messages import Message

from common.messages import (
    Message,
    MsgRegisterBet,
    MsgRegisterBetOk,
    MsgRegisterBetFailed,
)


class Protocol:
    """
    Protocol handler for the bet registration server.

    This class provides a higher-level abstraction over raw sockets,
    handling the details of the custom binary protocol. It is used
    to manage client connections and message exchange.
    """

    NULL_ADDR = ("", 0)

    def __init__(self, port: int, listen_backlog: int, logger: Logger):
        """
        Initializes the protocol with a listening socket.

        Parameters
        ----------
        port : int
            Port number to bind the server socket to.
        listen_backlog : int
            Maximum number of queued connections.
        logger : Logger
            Logger instance for recording protocol events.
        """
        self._socket: Socket = Socket(port, listen_backlog)
        self._logger: Logger = logger

    def accept_new_connection(self) -> Tuple[Tuple[str, int], Optional[Socket]]:
        """
        Wait for a new client connection.

        Blocks until a client connects or the listening socket is closed.
        Returns the client socket on success, or None if the server is
        shutting down.

        Returns
        -------
        Tuple[Tuple[str, int], Optional[Socket]]
            A tuple containing the client address (IP, port) and the
            client socket. If the server is shutting down, returns
            (NULL_ADDR, None).
        """
        self._logger.info("action: accept_connections | result: in_progress")

        try:
            addr, client_socket = self._socket.accept()
            self._logger.info(
                f"action: accept_connections | result: success | ip: {addr[0]}"
            )
            return addr, client_socket
        except OSError:
            # Socket was closed -> shutdown
            self._logger.info(
                f"action: server_welcomming_socket_shutdown | result: success"
            )

        return Protocol.NULL_ADDR, None

    def receive_message(self, client_sock: Socket) -> Message:
        """
        Receive a protocol message from a client socket.

        Parameters
        ----------
        client_sock : Socket
            The client socket to read from.

        Returns
        -------
        Message
            The decoded protocol message.
        """
        return client_sock.receive_message()

    def send_register_bet_ok(self, client_sock: Socket, dni: int, number: int) -> None:
        """
        Send a `MsgRegisterBetOk` response to the client.

        Parameters
        ----------
        client_sock : Socket
            The client socket to send the message to.
        dni : int
            Document number of the bettor.
        number : int
            Bet number confirmed by the server.
        """
        msg: MsgRegisterBetOk = MsgRegisterBetOk(dni, number)
        client_sock.send_message(msg)

    def send_register_bet_failed(
        self, client_sock: Socket, bet_bni: int, bet_number: int, failure_reason: int
    ) -> None:
        """
        Send a `MsgRegisterBetFailed` response to the client.

        Parameters
        ----------
        client_sock : Socket
            The client socket to send the message to.
        bet_dni : int
            DNI of the bettor (or UNKNOWN_BET_INFO if unknown).
        bet_number : int
            Bet number attempted (or UNKNOWN_BET_INFO if unknown).
        failure_reason : int
            Error code indicating the reason for failure.
        """
        msg: MsgRegisterBetFailed = MsgRegisterBetFailed(
            bet_bni, bet_number, failure_reason
        )
        client_sock.send_message(msg)

    def shutdown(self) -> None:
        """
        Shut down the listening server socket.

        Closes the main server socket, preventing new connections,
        and logs the shutdown event.
        """
        self._socket.shutdown()
        self._logger.info("action: server_welcomming_socket_closed  | result: success")

    def shutdown_socket(self, a_socket: Socket) -> None:
        """
        Shut down a client connection socket.

        Closes the given client socket and logs the shutdown event.

        Parameters
        ----------
        a_socket : Socket
            The client socket to close.
        """
        a_socket.shutdown()
        self._logger.info("action: client_connection_socket_closed  | result: success")
