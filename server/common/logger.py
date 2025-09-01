import logging
from multiprocessing import Queue
from logging.handlers import QueueHandler, QueueListener
from logging import Formatter, StreamHandler, Logger


class LoggerHandler:
    """
    Provides a multiprocessing-safe logging setup using a queue and listener.

    Log records are sent to a queue via QueueHandler and consumed by a
    QueueListener, ensuring logs from multiple processes are handled
    consistently and without conflicts.
    """

    MAX_LOG_QUEUE_SIZE: int = 10_000
    LOG_FORMAT: str = "%(asctime)s %(levelname)-8s %(message)s"
    LOG_DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    DEFAULT_LOG_LEVEL: int = logging.INFO

    def __init__(self, level: str):
        """
        Initialize the logging system with a queue and console handler.

        Parameters
        ----------
        level : str
            Logging level name (e.g., "INFO", "DEBUG"). Defaults to INFO if invalid.
        """
        self.log_level: int = getattr(logging, level, self.DEFAULT_LOG_LEVEL)

        self._log_queue: Queue = Queue(maxsize=self.MAX_LOG_QUEUE_SIZE)

        formatter: Formatter = logging.Formatter(
            fmt=self.LOG_FORMAT,
            datefmt=self.LOG_DATETIME_FORMAT,
        )

        console_handler: StreamHandler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self._listener: QueueListener = QueueListener(self._log_queue, console_handler)

        self._root_logger: Logger = logging.getLogger()
        self._root_logger.setLevel(self.log_level)

    def start(self) -> None:
        """Start the queue listener to process log records."""
        self._listener.start()

    def stop(self) -> None:
        """
        Stop the listener and clean up resources.

        Removes queue handlers, closes the queue, and logs a final
        shutdown message using a direct logger.
        """
        self._listener.stop()

        for handler in list(self._root_logger.handlers):
            if isinstance(handler, QueueHandler):
                self._root_logger.removeHandler(handler)

        self._log_queue.close()
        self._log_queue.join_thread()
        LoggerHandler.get_direct_logger(
            self.LOG_FORMAT, self.LOG_DATETIME_FORMAT, self.log_level
        ).info("action: logger_queue_resources_closed  | result: success")

    def get_logger(self) -> Logger:
        """
        Return a logger configured with a QueueHandler.

        Ensures log records are sent to the multiprocessing queue
        instead of being written directly.
        """
        logger: Logger = logging.getLogger()

        # clear existing handlers
        logger.handlers = []

        logger.addHandler(QueueHandler(self._log_queue))
        logger.setLevel(self._root_logger.level)
        return logger

    @staticmethod
    def get_direct_logger(
        log_format: str, log_datetime_format: str, log_level: int
    ) -> Logger:
        """
        Return a direct logger that bypasses the queue.

        Useful for logging after the queue has been closed, such as
        during shutdown or error handling.
        """
        logger = logging.getLogger()
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    fmt=log_format,
                    datefmt=log_datetime_format,
                )
            )
            logger.addHandler(handler)
            logger.setLevel(log_level)
            logger.propagate = False
        return logger
