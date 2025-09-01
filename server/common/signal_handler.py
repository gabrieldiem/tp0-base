import signal
from logging import Logger
from common.server import Server
from types import FrameType
from typing import Optional


class SignalHandler:
    """
    Handles termination signals (SIGINT, SIGTERM) to ensure the server
    is stopped cleanly and shutdown events are logged.
    """

    def __init__(self, server: Server, logger: Logger):
        """
        Create a SignalHandler bound to a server and logger.
        """
        self._server = server
        self._logger = logger

    def __handle_signal(self, signum: int, _frame: Optional[FrameType]) -> None:
        """
        Invoked when a registered signal is received.
        Logs the signal and requests the server to stop.
        """
        self._logger.info(
            f"action: signal_with_code_{signum}_received | result: success"
        )
        self._server.stop()
        self._logger.info("action: server_shutdown | result: success")

    def register(self) -> None:
        """
        Register handlers for SIGINT and SIGTERM.
        """
        signal.signal(signal.SIGINT, self.__handle_signal)
        signal.signal(signal.SIGTERM, self.__handle_signal)
