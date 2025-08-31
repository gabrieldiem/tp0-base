import signal
from logging import Logger
from common.server import Server

class SignalHandler:
    def __init__(self, server: Server, logger: Logger):
        self.server = server
        self.logger = logger

    def __call__(self, signum, frame) -> None:
        """Make the instance callable so it can be used as a signal handler"""
        self.logger.info(
            f"action: signal_received | signal_number: {signum}"
        )
        self.server.stop()
        self.server.join()
        self.logger.info("action: shutdown | result: success")

    def register(self) -> None:
        """Register the handler for SIGINT and SIGTERM"""
        signal.signal(signal.SIGINT, self)
        signal.signal(signal.SIGTERM, self)
