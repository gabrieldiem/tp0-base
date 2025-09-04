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

    Responsibilities:
    - Accept connections from multiple agencies (clients).
    - Handle bet registration requests (`MsgRegisterBets`).
    - Store bets in persistent storage.
    - Track readiness state of each agency (sending, ready, waiting, winners received).
    - Once all agencies are ready, compute winners and send them back.
    - Handle graceful shutdown on stop.
    """

    # Loop control constants
    STOP = 0
    CONTINUE = 1
    CONTINUE_SAFE_TO_END = 2

    # Agency states
    AGENCY_SENDING_BETS = 10
    AGENCY_READY_FOR_LOTTERY = 20
    AGENCY_WAITING_FOR_LOTTERY = 30
    AGENCY_GOT_LOTTERY_WINNERS = 40

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
        number_of_agencies : int
            Maximum number of agencies (clients) expected.
        logger : Logger
            Logger instance for recording server events.
        """
        self._protocol = Protocol(port, listen_backlog, logger)
        self._max_agencies: int = number_of_agencies
        self._logger: Logger = logger
        self._running: bool = False
        self._stopped: bool = False

        # Track readiness state of each agency (by port)
        self._readiness_status: Dict[int, int] = {}

        # Map client port → agency ID (from bets)
        self._agency_id_by_port: Dict[int, int] = {}

        # Active client sockets
        self._clients: List[Socket] = []

        # Winners storage
        self._winners: List[Tuple[int, int]] = []
        self._winners_per_agency: Dict[int, List[int]] = {}

    def run(self) -> None:
        """
        Start the main server loop with select-based multiplexing.
        Handles up to `_max_agencies` clients concurrently in a single thread.
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
                # Wait for activity on any socket
                readable, _, _ = select.select(read_sockets, [], [])
            except OSError as e:
                # select() failed (likely due to shutdown)
                if (
                    keep_handling_client != Server.CONTINUE_SAFE_TO_END
                    and self._running
                ):
                    self._logger.error(
                        f"action: select_socket_to_read | result: fail | error: {e}"
                    )
                break

            # Handle all sockets that are ready
            for sock in readable:
                if sock is welcomming_socket:
                    # New incoming connection
                    self.__handle_new_connection(welcomming_socket)
                else:
                    # Existing client sent data
                    keep_handling_client = self.__handle_current_connection(
                        sock, keep_handling_client
                    )

        # Cleanup if not already stopped
        if not self._stopped:
            for client_socket in self._clients:
                self._protocol.shutdown_socket(client_socket)

            self._clients = []
            self._protocol.shutdown()

    def __handle_new_connection(self, welcomming_socket: StdSocket) -> None:
        """
        Accept a new client connection if capacity allows.
        Rejects the connection if max agencies already connected.
        """
        if len(self._clients) >= self._max_agencies:
            self._logger.warning(
                "action: accept_connections | result: fail | reason: max_clients_reached"
            )
            # Accept and immediately close the connection
            addr, client_socket = welcomming_socket.accept()
            self._protocol.shutdown_socket(Socket.__from_existing(client_socket))
            return

        addr, client_socket = self._protocol.accept_new_connection()
        if client_socket:
            self._clients.append(client_socket)

    def __handle_current_connection(
        self, client_sock: StdSocket, keep_handling_client: int
    ) -> int:
        """
        Handle an incoming message from an existing client connection.
        """
        if not self._running:
            return Server.STOP

        # Find the wrapped Socket object for this raw socket
        client = next(c for c in self._clients if c.get_socket() is client_sock)

        try:
            # Decode message from client
            msg = client.receive_message()

            # Identify agency by its port (temporary ID until bets reveal agency ID)
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
            # If error occurs, close client connection
            if keep_handling_client != Server.CONTINUE_SAFE_TO_END:
                self._logger.error(
                    f"action: receive_message | result: fail | error: {e}"
                )

            self._protocol.shutdown_socket(client)
            self._clients.remove(client)
            return keep_handling_client

    def send_message_response(self, client_sock: Socket, msg: Message) -> int:
        """
        Dispatch message and send response.

        - `MsgRegisterBets`: store bets, send OK/Fail → CONTINUE
        - `MsgAck`: acknowledge → CONTINUE (if lottery done, may end)
        - `MsgAllBetsSent`: mark agency ready → CONTINUE (if all ready, run lottery)
        - `MsgRequestWinners`: if lottery done, send winners → CONTINUE_SAFE_TO_END
        - Unknown: send failure → STOP
        """
        if isinstance(msg, MsgRegisterBets):
            # Client is sending bets
            agencyPort = client_sock.get_port()
            self._readiness_status[agencyPort] = Server.AGENCY_SENDING_BETS
            self._agency_id_by_port[agencyPort] = msg.get_bets()[0]._agency

            self.__process_batch_bet_registration(client_sock, msg)
            return Server.CONTINUE

        elif isinstance(msg, MsgAck):
            # Client acknowledged last message
            if self.__lottery_occurred():
                return Server.CONTINUE_SAFE_TO_END
            return Server.CONTINUE

        elif isinstance(msg, MsgAllBetsSent):
            # Agency finished sending bets
            agencyPort = client_sock.get_port()
            self._readiness_status[agencyPort] = Server.AGENCY_READY_FOR_LOTTERY

            if self.__all_agencies_ready():
                # All agencies ready → compute and send winners
                self.__do_lottery()
                self.__inform_winners_to_waiting_agencies()
                return Server.CONTINUE_SAFE_TO_END

            return Server.CONTINUE

        elif isinstance(msg, MsgRequestWinners):
            # Agency requests winners
            agencyPort = client_sock.get_port()
            self._readiness_status[agencyPort] = Server.AGENCY_WAITING_FOR_LOTTERY

            if self.__lottery_occurred():
                # Lottery already done → send winners
                self.__inform_winners_to_waiting_agencies()
                return Server.CONTINUE_SAFE_TO_END
            else:
                # Not all agencies ready yet
                agency = self._agency_id_by_port.get(agencyPort)
                self._logger.info(
                    f"action: agency_{agency}_waiting | result: in_progress"
                )

            return Server.CONTINUE

        else:
            # Unknown message type → send failure response
            self._protocol.send_register_bets_failed(
                client_sock, FAILURE_UNKNOWN_MESSAGE
            )
            self._logger.error("action: mensaje_desconocido | result: fail")
            return Server.STOP

    def __lottery_occurred(self) -> bool:
        """Return True if winners have already been computed."""
        return len(self._winners) > 0

    def __all_agencies_ready(self) -> bool:
        """
        Return True if all agencies are connected and none are still sending bets.
        """

        # Ensure all expected agencies are connected
        are_all_agencies_connected = len(self._clients) == self._max_agencies
        if not are_all_agencies_connected:
            return False

        # Check readiness state of all agencies
        for status in self._readiness_status.values():
            if status == Server.AGENCY_SENDING_BETS:
                return False

        return True

    def __do_lottery(self):
        """
        Compute winners and group them by agency.
        """
        bets: List[Bet] = load_bets()

        # Collect all winning bets (agency, dni)
        for bet in bets:
            if has_won(bet):
                self._winners.append((int(bet.agency), int(bet.document)))

        # Group winners by agency
        for agency, dni in self._winners:
            if agency not in self._winners_per_agency:
                self._winners_per_agency[agency] = []
            self._winners_per_agency[agency].append(dni)

        self._logger.info("action: sorteo | result: success")

    def __inform_winners_to_waiting_agencies(self):
        """
        Send winners to each connected agency that is waiting for them.
        """

        # Send winners to each connected client
        for client in self._clients:
            agencyPort: int = client.get_port()
            if (
                self._readiness_status.get(agencyPort)
                == Server.AGENCY_WAITING_FOR_LOTTERY
            ):
                agencyId: Optional[int] = self._agency_id_by_port.get(agencyPort)

                if agencyId:
                    dni_winners = self._winners_per_agency.get(agencyId, [])
                    self._logger.info(
                        f"action: inform_winners | result: success | client: {agencyId}"
                    )
                    self._protocol.inform_winners(client, dni_winners)
                    # Mark agency as having received winners
                    self._readiness_status[agencyPort] = (
                        Server.AGENCY_GOT_LOTTERY_WINNERS
                    )

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
        except Exception:
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

        # Close all client sockets
        for client_sock in self._clients:
            self._protocol.shutdown_socket(client_sock)

        self._clients = []

        # Close listening socket
        self._protocol.shutdown()
        self._stopped = True
