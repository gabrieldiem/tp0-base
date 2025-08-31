import logging
from multiprocessing import Queue
from logging.handlers import QueueHandler, QueueListener
from logging import Formatter, StreamHandler, Logger


class CustomLogger:
    MAX_LOG_QUEUE_SIZE: int = 10_000
    LOG_FORMAT: str = "%(asctime)s %(levelname)-8s %(message)s"
    LOG_DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    def __init__(self, level: str):
        level_parsed: int = logging.getLevelNamesMapping()[level]

        self.log_queue: Queue = Queue(maxsize=self.MAX_LOG_QUEUE_SIZE)

        formatter: Formatter = logging.Formatter(
            fmt=self.LOG_FORMAT,
            datefmt=self.LOG_DATETIME_FORMAT,
        )

        console_handler: StreamHandler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.listener: QueueListener = QueueListener(self.log_queue, console_handler)

        self.root_logger: Logger = logging.getLogger()
        self.root_logger.setLevel(level_parsed)

    def start(self):
        """Start the listener"""
        self.listener.start()

    def stop(self):
        """Stop the listener gracefully"""
        self.listener.stop()

    def get_logger(self) -> Logger:
        """
        Get a logger that sends records to the queue.
        Multiprocessing-safe
        """
        logger: Logger = logging.getLogger()

        # clear existing handlers
        logger.handlers = []

        logger.addHandler(QueueHandler(self.log_queue))
        logger.setLevel(self.root_logger.level)
        return logger
