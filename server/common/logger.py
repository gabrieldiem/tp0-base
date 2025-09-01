import logging
from logging import Logger, StreamHandler


class LoggerHandler:
    """
    Utility for creating loggers with a consistent format.

    Provides a static method to return a logger that writes to stdout
    with a standard format and log level.
    """

    LOG_FORMAT: str = "%(asctime)s %(levelname)-8s %(message)s"
    LOG_DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    DEFAULT_LOG_LEVEL: int = logging.INFO

    @staticmethod
    def get_logger(level: str) -> Logger:
        """
        Return a logger configured with a stream handler, formatter,
        and the given log level.

        If the level string is invalid, INFO is used by default.
        """
        log_level: int = getattr(logging, level, LoggerHandler.DEFAULT_LOG_LEVEL)
        logger: Logger = logging.getLogger()
        handler: StreamHandler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                fmt=LoggerHandler.LOG_FORMAT,
                datefmt=LoggerHandler.LOG_DATETIME_FORMAT,
            )
        )
        logger.addHandler(handler)
        logger.setLevel(log_level)
        return logger
