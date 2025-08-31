#!/usr/bin/env python3

from configparser import ConfigParser
from common.server import Server
from common.logger import Logger
import os

GENERIC_ERROR_CODE = 1
SUCCESS_CODE = 0

def initialize_config():
    """ Parse env variables or config file to find program config params

    Function that search and parse program configuration parameters in the
    program environment variables first and the in a config file. 
    If at least one of the config parameters is not found a KeyError exception 
    is thrown. If a parameter could not be parsed, a ValueError is thrown. 
    If parsing succeeded, the function returns a ConfigParser object 
    with config parameters
    """

    config = ConfigParser(os.environ)
    # If config.ini does not exists original config object is not modified
    config.read("config.ini")

    config_params = {}
    try:
        config_params["port"] = int(os.getenv('SERVER_PORT', config["DEFAULT"]["SERVER_PORT"]))
        config_params["listen_backlog"] = int(os.getenv('SERVER_LISTEN_BACKLOG', config["DEFAULT"]["SERVER_LISTEN_BACKLOG"]))
        config_params["logging_level"] = os.getenv('LOGGING_LEVEL', config["DEFAULT"]["LOGGING_LEVEL"])
    except KeyError as e:
        raise KeyError("Key was not found. Error: {} .Aborting server".format(e))
    except ValueError as e:
        raise ValueError("Key could not be parsed. Error: {}. Aborting server".format(e))

    return config_params

def main() -> int:
    """
    Returns the exit code where a non-zero exit code means there was an error
    """
    try:
        config_params = initialize_config()
        logging_level = config_params["logging_level"]
        port = config_params["port"]
        listen_backlog = config_params["listen_backlog"]

        logger_starter = Logger(level=logging_level)
        logger_starter.start()
        
        logger = logger_starter.get_logger()

        # Log config parameters at the beginning of the program to verify the configuration
        # of the component
        logger.debug(f"action: config | result: success | port: {port} | "
                    f"listen_backlog: {listen_backlog} | logging_level: {logging_level}")

        # Initialize server and start server loop
        server = Server(port, listen_backlog, logger)
        server.run()
        return SUCCESS_CODE
    
    except Exception as e:
        print("Exception:", e)
        return GENERIC_ERROR_CODE


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
