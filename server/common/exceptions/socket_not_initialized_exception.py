class SocketNotInitializedException(Exception):
    def __init__(self, message="Tried to start with an uninitlized socket"):
        self.message = message

    def __repr__(self) -> str:
        return f"SocketNotInitializedException: {self.message})"
