import logging
import multiprocessing
from logging.handlers import QueueHandler, QueueListener


class Logger:
    MAX_LOG_QUEUE_SIZE = 10_000
    LOG_FORMAT = "%(asctime)s %(levelname)-8s %(message)s"
    LOG_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, level=logging.INFO):
        self.log_queue = multiprocessing.Queue(maxsize=self.MAX_LOG_QUEUE_SIZE)

        formatter = logging.Formatter(
            fmt=self.LOG_FORMAT,
            datefmt=self.LOG_DATETIME_FORMAT,
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.listener = QueueListener(self.log_queue, console_handler)

        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(level)

    def start(self):
        """Start the listener"""
        self.listener.start()

    def stop(self):
        """Stop the listener gracefully"""
        self.listener.stop()

    def get_logger(self):
        """
        Get a logger that sends records to the queue.
        Multiprocessing-safe
        """
        logger = logging.getLogger()

        # clear existing handlers
        logger.handlers = []

        logger.addHandler(QueueHandler(self.log_queue))
        logger.setLevel(self.root_logger.level)
        return logger
