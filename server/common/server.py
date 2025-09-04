from logging import Logger
from common.protocol import Protocol
from common.socket import Socket
from typing import Tuple, Optional, List, Dict
from common.utils import Bet, store_bets, load_bets, has_won
import select
from socket import socket as StdSocket

from common.messages import (
    Message,
    MsgRegisterBets,
    StandardBet,
    MsgAck,
    MsgAllBetsSent,
    MsgRequestWinners,
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

    AGENCY_SENDING_BETS = 10
    AGENCY_READY_FOR_LOTTERY = 20
    AGENCY_WAITING_FOR_LOTTERY = 30

    def __init__(
        self, port: int, listen_backlog: int, number_of_agencies: int, logger: Logger
    ):
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
        self._max_agencies: int = number_of_agencies
        self._logger: Logger = logger
        self._running: bool = False
        self._stopped: bool = False
        self._readiness_status = {}
        self._agency_id_by_port = {}

        self._clients: List[Socket] = []

    def run(self) -> None:
        """
        Start the main server loop with select-based multiplexing.
        Handles up to MAX_CLIENTS clients concurrently in a single thread.
        """
        self._running = True
        self._logger.info("action: starting_loop | result: success")

        if self._stopped:
            return

        welcomming_socket = self._protocol.get_socket()
        keep_handling_client: int = Server.CONTINUE

        while self._running and keep_handling_client != Server.STOP:

            # Build the read set: listening socket + all client sockets
            read_sockets = [welcomming_socket] + [c.get_socket() for c in self._clients]

            try:
                readable, _, _ = select.select(read_sockets, [], [])
            except OSError as e:
                if (
                    keep_handling_client != Server.CONTINUE_SAFE_TO_END
                    and self._running
                ):
                    self._logger.error(
                        f"action: select_socket_to_read | result: fail | error: {e}"
                    )
                break

            for sock in readable:
                if sock is welcomming_socket:
                    self.__handle_new_connection(welcomming_socket)
                else:
                    keep_handling_client = self.__handle_current_connection(
                        sock, keep_handling_client
                    )

        if not self._stopped:
            for client_socket in self._clients:
                self._protocol.shutdown_socket(client_socket)

            self._clients = []
            self._protocol.shutdown()

    def __handle_new_connection(self, welcomming_socket: StdSocket) -> None:
        if len(self._clients) >= self._max_agencies:
            self._logger.warning(
                "action: accept_connections | result: fail | reason: max_clients_reached"
            )
            addr, client_socket = welcomming_socket.accept()
            self._protocol.shutdown_socket(Socket.__from_existing(client_socket))
            return

        addr, client_socket = self._protocol.accept_new_connection()
        if client_socket:
            self._clients.append(client_socket)

    def __handle_current_connection(
        self, client_sock: StdSocket, keep_handling_client: int
    ) -> int:
        if not self._running:
            return Server.STOP

        client = next(c for c in self._clients if c.get_socket() is client_sock)

        try:
            msg = client.receive_message()

            agencyPort = client_sock.getpeername()[1]
            agency = (
                self._agency_id_by_port.get(agencyPort)
                if self._agency_id_by_port.get(agencyPort)
                else agencyPort
            )
            self._logger.info(
                f"action: receive_message | result: success | msg: {msg} | client: {agency}"
            )

            return self.send_message_response(client, msg)

        except (ConnectionError, ValueError, OSError) as e:
            if keep_handling_client == Server.CONTINUE_SAFE_TO_END:
                self._logger.error(
                    f"action: receive_message | result: fail | error: {e}"
                )

            self._protocol.shutdown_socket(client)
            self._clients.remove(client)
            return Server.CONTINUE

    def send_message_response(self, client_sock: Socket, msg: Message) -> int:
        """
        Dispatch message and send response.

        - `MsgRegisterBets`: store bets, send OK/Fail → CONTINUE_SAFE_TO_END
        - `MsgAck`: stop handling client → STOP
        - Unknown: send failure → STOP
        """
        if isinstance(msg, MsgRegisterBets):
            message: MsgRegisterBets = msg
            agencyPort = client_sock.get_port()
            self._readiness_status[agencyPort] = Server.AGENCY_SENDING_BETS
            self._agency_id_by_port[agencyPort] = msg.get_bets()[0]._agency

            self.__process_batch_bet_registration(client_sock, message)
            return Server.CONTINUE

        elif isinstance(msg, MsgAck):
            return Server.CONTINUE

        elif isinstance(msg, MsgAllBetsSent):
            agencyPort = client_sock.get_port()
            self._readiness_status[agencyPort] = Server.AGENCY_READY_FOR_LOTTERY
            return Server.CONTINUE

        elif isinstance(msg, MsgRequestWinners):
            agencyPort = client_sock.get_port()
            self._readiness_status[agencyPort] = Server.AGENCY_WAITING_FOR_LOTTERY

            if self.__all_agencies_waiting():
                self.__process_winners_request()
                return Server.CONTINUE_SAFE_TO_END
            else:
                agency = self._agency_id_by_port.get(
                    self._readiness_status.get(agencyPort)
                )
                self._logger.info(
                    f"action: agency_{agency}_waiting | result: in_progress"
                )

            return Server.CONTINUE

        else:
            # Unknown message type → send failure response
            self._protocol.send_register_bets_failed(
                client_sock, FAILURE_UNKNOWN_MESSAGE
            )
            self._logger.error(f"action: mensaje_desconocido | result: fail")
            return Server.STOP

    def __all_agencies_waiting(self) -> bool:
        """
        Return True if all agencies are in AGENCY_WAITING_FOR_LOTTERY state.
        """

        are_all_agencies_connected = len(self._clients) == self._max_agencies
        if not are_all_agencies_connected:
            return False

        are_all_agencies_ready = True

        for status in self._readiness_status.values():
            if status != Server.AGENCY_WAITING_FOR_LOTTERY:
                are_all_agencies_ready = False

        return are_all_agencies_ready

    def __process_winners_request(self):
        bets: List[Bet] = load_bets()
        winners: List[Tuple[int, int]] = []

        for bet in bets:
            if has_won(bet):
                winners.append((int(bet.agency), int(bet.document)))

        winners_per_agency: Dict[int, List[int]] = {}

        for agency, dni in winners:
            if agency not in winners_per_agency:
                winners_per_agency[agency] = []
            winners_per_agency[agency].append(dni)

        for client in self._clients:
            agencyPort: int = client.get_port()
            agencyId: Optional[int] = self._agency_id_by_port.get(agencyPort)

            if agencyId:
                dni_winners = winners_per_agency.get(agencyId)

                if dni_winners:
                    self._protocol.inform_winners(client, dni_winners)
                else:
                    self._protocol.inform_winners(client, [])

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
        self._running = False

        if self._stopped:
            return

        for client_sock in self._clients:
            self._protocol.shutdown_socket(client_sock)

        self._clients = []

        self._protocol.shutdown()
        self._stopped = True
