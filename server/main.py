#!/usr/bin/env python3

from configparser import ConfigParser
from common.server import Server
from common.logger import LoggerHandler
from common.signal_handler import SignalHandler
from logging import Logger
import os

# Logging format configuration
LOG_FORMAT: str = "%(asctime)s %(levelname)-8s %(message)s"
LOG_DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# Default config file path
CONFIG_FILEPATH: str = "config.ini"


def initialize_config() -> dict:
    """
    Parse environment variables or config file to find program config params.

    Priority:
      1. Environment variables (if set)
      2. Config file (config.ini, section DEFAULT)

    Required parameters:
      - SERVER_PORT (int)
      - SERVER_LISTEN_BACKLOG (int)
      - LOGGING_LEVEL (str)
      - NUM_AGENCIES (int, defaults to listen_backlog if not set)

    Raises
    ------
    KeyError
        If a required key is missing in both env and config file.
    ValueError
        If a parameter cannot be parsed into the expected type.

    Returns
    -------
    dict
        Dictionary with parsed configuration parameters.
    """

    config = ConfigParser(os.environ)
    # If config.ini does not exist, config object remains unchanged
    config.read(CONFIG_FILEPATH)

    config_params = {}
    try:
        # Port where the server will listen
        config_params["port"] = int(
            os.getenv("SERVER_PORT", config["DEFAULT"]["SERVER_PORT"])
        )

        # Maximum number of queued connections
        config_params["listen_backlog"] = int(
            os.getenv(
                "SERVER_LISTEN_BACKLOG", config["DEFAULT"]["SERVER_LISTEN_BACKLOG"]
            )
        )

        # Logging level (DEBUG, INFO, ERROR, etc.)
        config_params["logging_level"] = os.getenv(
            "LOGGING_LEVEL", config["DEFAULT"]["LOGGING_LEVEL"]
        )

        # Number of agencies (defaults to listen_backlog if not explicitly set)
        config_params["number_of_agencies"] = int(
            os.getenv("NUM_AGENCIES", config_params["listen_backlog"])
        )

    except KeyError as e:
        raise KeyError(f"Key was not found. Error: {e}. Aborting server")
    except ValueError as e:
        raise ValueError(f"Key could not be parsed. Error: {e}. Aborting server")

    return config_params


def main() -> None:
    """
    Main entry point of the program.

    Initializes configuration, logging, server, and signal handling.
    Starts the server loop. If an exception occurs, logs the error
    and exits with a non-zero exit code.
    """
    try:
        config_params: dict = initialize_config()
        logging_level: str = config_params["logging_level"]
        port: int = config_params["port"]
        listen_backlog: int = config_params["listen_backlog"]
        number_of_agencies: int = config_params["number_of_agencies"]

        logger: Logger = LoggerHandler.get_logger(logging_level)

        # Log config parameters at the beginning of the program to verify the configuration
        # of the component
        logger.debug(
            f"action: config | result: success | port: {port} | "
            f"listen_backlog: {listen_backlog} | logging_level: {logging_level}"
        )

        # Initialize server
        server: Server = Server(port, listen_backlog, number_of_agencies, logger)

        # Register signal handler
        signal_handler: SignalHandler = SignalHandler(server, logger)
        signal_handler.register()

        server.run()

    except Exception as e:
        # Get new logger to log error to ensure it isn't corrupted
        LoggerHandler.get_logger("ERROR").error(
            f"action: main | result: fail | error: {e.__class__}:{e}"
        )


if __name__ == "__main__":
    main()
