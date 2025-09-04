from logging import Logger
from common.protocol import Protocol
from common.socket import Socket
from typing import Tuple, Optional, List
from common.utils import Bet, store_bets

from common.messages import (
    Message,
    MsgRegisterBets,
    StandardBet,
    MsgAck,
    FAILURE_UNKNOWN_MESSAGE,
    FAILURE_COULD_NOT_PROCESS_BET,
)


class Server:
    """
    TCP bet registration server.

    The server listens on a given port, accepts client connections,
    and processes messages defined by the custom binary protocol.
    It specifically handles bet registration requests in batches (`MsgRegisterBets`),
    converts them into domain `Bet` objects, stores them, and responds
    with either a success (`MsgRegisterBetOk`) or failure
    (`MsgRegisterBetFailed`) message.

    The server runs in a loop until explicitly stopped, ensuring
    clean shutdown of sockets and proper logging of all events.
    """

    STOP = 0
    CONTINUE = 1
    CONTINUE_SAFE_TO_END = 2

    def __init__(self, port: int, listen_backlog: int, logger: Logger):
        """
        Initialize the server with a listening socket and logger.

        Parameters
        ----------
        port : int
            Port number to bind the server to.
        listen_backlog : int
            Maximum number of queued connections.
        logger : Logger
            Logger instance for recording server events.
        """
        self._protocol = Protocol(port, listen_backlog, logger)
        self._logger: Logger = logger
        self._running: bool = False
        self._stopped: bool = False
        self._client: Optional[Socket] = None

    def run(self) -> None:
        """
        Start the main server loop.

        Continuously accepts new client connections and handles them
        one at a time. For each connection, the server receives a
        protocol message, processes it, and sends an appropriate
        response. The loop stops when the server is explicitly
        stopped or the listening socket is closed.
        """
        self._running = True
        self._logger.info(f"action: starting_loop | result: success")

        if self._stopped:
            return

        while self._running:
            addr, client_sock = self._protocol.accept_new_connection()

            if not client_sock:
                break
            self._client = client_sock

            self.__handle_client_connection(self._client, addr)

    def __handle_client_connection(
        self, client_sock: Socket, client_addr: Tuple[str, int]
    ) -> None:
        """
        Handle a single client connection.

        Reads messages from the client in a loop, logs them, and
        dispatches them to the appropriate handler. If the message
        is a valid `MsgRegisterBets`, it is converted into `Bet`
        objects and stored. If it's a `MsgAck`, the connection is
        closed gracefully. Otherwise, a failure response is sent.

        Parameters
        ----------
        client_sock : Socket
            The client socket for communication.
        client_addr : Tuple[str, int]
            The client address (IP, port).
        """
        keep_handling_client: int = Server.CONTINUE

        while keep_handling_client in [Server.CONTINUE, Server.CONTINUE_SAFE_TO_END]:
            try:
                msg: Message = self._protocol.receive_message(client_sock)
                self._logger.info(
                    f"action: receive_message | result: success | ip: {client_addr[0]} | msg: {msg}"
                )

                if self._running:
                    keep_handling_client = self.send_message_response(client_sock, msg)

            except (ConnectionError, ValueError, OSError) as e:
                if keep_handling_client != Server.CONTINUE_SAFE_TO_END:
                    self._logger.error(
                        f"action: receive_message | result: fail | error: {e}"
                    )

                keep_handling_client = Server.STOP
                break

        self._protocol.shutdown_socket(client_sock)

    def send_message_response(self, client_sock: Socket, msg: Message) -> int:
        """
        Dispatch message and send response.

        - `MsgRegisterBets`: store bets, send OK/Fail → CONTINUE_SAFE_TO_END
        - `MsgAck`: stop handling client → STOP
        - Unknown: send failure → STOP
        """
        if isinstance(msg, MsgRegisterBets):
            message: MsgRegisterBets = msg
            self.__process_batch_bet_registration(client_sock, message)
            return Server.CONTINUE_SAFE_TO_END
        elif isinstance(msg, MsgAck):
            return Server.CONTINUE_SAFE_TO_END
        else:
            # Unknown message type → send failure response
            self._protocol.send_register_bets_failed(
                client_sock, FAILURE_UNKNOWN_MESSAGE
            )
            self._logger.error(f"action: mensaje_desconocido | result: fail")
            return Server.STOP

    def __process_batch_bet_registration(
        self, client_sock: Socket, msg: MsgRegisterBets
    ):
        """
        Process a batch bet registration request.

        Converts the received `StandardBet` objects into domain `Bet`
        objects, stores them, and sends either a success or failure
        response back to the client.
        """
        standard_bets: List[StandardBet] = msg.get_bets()

        # Attempt to store bets in persistent storage
        storing_success: bool = self.__store_bets(standard_bets)

        if storing_success:
            # Acknowledge success
            self._protocol.send_register_bets_ok(client_sock)

            self._logger.info(
                f"action: apuesta_recibida | result: success | cantidad: {len(standard_bets)}"
            )
            return

        # If storing failed, send failure response
        self._protocol.send_register_bets_failed(
            client_sock, FAILURE_COULD_NOT_PROCESS_BET
        )
        self._logger.info(
            f"action: apuesta_recibida | result: fail | cantidad: {len(standard_bets)}"
        )

    def __store_bets(self, standard_bets: List[StandardBet]) -> bool:
        """
        Convert protocol-level bets into domain `Bet` objects and store them.

        Parameters
        ----------
        standard_bets : List[StandardBet]
            List of bets received from the client.

        Returns
        -------
        bool
            True if storing succeeded, False otherwise.
        """
        bets: List[Bet] = []
        for bet in standard_bets:
            bets.append(bet.to_utility_bet())

        try:
            store_bets(bets)
            return True
        except Exception as e:
            # Any exception during storage is treated as a failure
            return False

    def stop(self) -> None:
        """
        Stop the server.

        Shuts down and closes the listening socket, sets the server
        state to stopped, and prevents further connections.
        """
        if self._stopped:
            return

        if self._client:
            self._protocol.shutdown_socket(self._client)
            self._client = None

        self._protocol.shutdown()
        self._stopped = True
        self._running = False
