import signal
from logging import Logger
from common.server import Server
from types import FrameType
from typing import Optional
from common.logger import LoggerHandler


class SignalHandler:
    def __init__(self, server: Server, logger: Logger, loggers_handler: LoggerHandler):
        self._server = server
        self._logger = logger
        self._loggers_handler = loggers_handler

    def __handle_signal(self, signum: int, _frame: Optional[FrameType]) -> None:
        """Logs the signal number and stops the Server"""
        self._logger.info(
            f"action: signal_with_code_{signum}_received | result: success"
        )
        self._server.stop()
        self._logger.info("action: server_shutdown | result: success")

    def register(self) -> None:
        """Register the handler for SIGINT and SIGTERM"""
        signal.signal(signal.SIGINT, self.__handle_signal)
        signal.signal(signal.SIGTERM, self.__handle_signal)
