import signal
from logging import Logger
from common.server import Server
from types import FrameType
from typing import Optional


class SignalHandler:
    def __init__(self, server: Server, logger: Logger):
        self._server = server
        self._logger = logger

    def __handle_signal(self, signum: int, _frame: Optional[FrameType]) -> None:
        """Logs the signal number and stops the Server"""
        self._logger.info(f"action: signal_received | signal_number: {signum}")
        self._server.stop()
        self._server.join()
        self._logger.info("action: shutdown | result: success")

    def register(self) -> None:
        """Register the handler for SIGINT and SIGTERM"""
        signal.signal(signal.SIGINT, self.__handle_signal)
        signal.signal(signal.SIGTERM, self.__handle_signal)
