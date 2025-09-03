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
    NULL_ADDR = ("", 0)

    def __init__(self, port: int, listen_backlog: int, logger: Logger):
        self._socket: Socket = Socket(port, listen_backlog)
        self._logger: Logger = logger

    def accept_new_connection(self) -> Tuple[Tuple[str, int], Optional[Socket]]:
        """
        Wait for a new client connection.

        Blocks until a client connects or the listening socket is closed.
        Returns the client socket on success, or None if the server is
        shutting down.
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
        return client_sock.receive_message()

    def send_register_bet_ok(self, client_sock: Socket, dni: int, number: int) -> None:
        msg: MsgRegisterBetOk = MsgRegisterBetOk(dni, number)
        client_sock.send_message(msg)

    def send_register_bet_failed(self, client_sock: Socket) -> None:
        msg: MsgRegisterBetFailed = MsgRegisterBetFailed(0, 0, 1)
        client_sock.send_message(msg)

    def shutdown(self) -> None:
        self._socket.shutdown()
        self._logger.info("action: server_welcomming_socket_closed  | result: success")

    def shutdown_socket(self, a_socket: Socket) -> None:
        a_socket.shutdown()
        self._logger.info("action: client_connection_socket_closed  | result: success")
