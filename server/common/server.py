from logging import Logger
from common.protocol import Protocol
from common.socket import Socket
from typing import Tuple, Optional, List
from common.utils import Bet
from common.lottery_monitor import LotteryMonitor
from multiprocessing import Process

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
        self._protocol = Protocol(port, listen_backlog, logger)
        self._max_agencies: int = number_of_agencies
        self._logger: Logger = logger
        self._running: bool = False
        self._stopped: bool = False

        # Shared monitor for readiness, agency mapping, and winners
        self._lottery_monitor: LotteryMonitor = LotteryMonitor()

        # Track child processes
        self._processes: List[Process] = []

    def run(self) -> None:
        """
        Main loop: accept new connections and spawn a process for each client.
        """
        self._running = True
        self._logger.info("action: starting_loop | result: success")

        if self._stopped:
            return

        while self._running:
            try:
                addr, client_socket = self._protocol.accept_new_connection()
                if client_socket:
                    # Spawn a new process to handle this client
                    p = Process(
                        target=self._handle_client_process,
                        args=(
                            client_socket,
                            addr,
                            self._lottery_monitor,
                        ),
                    )
                    p.start()
                    self._processes.append(p)
            except OSError as e:
                if self._running:
                    self._logger.error(
                        f"action: accept_connection | result: fail | error: {e}"
                    )
                break

        # Cleanup
        if not self._stopped:
            self._protocol.shutdown()
            for p in self._processes:
                p.join()

    def _handle_client_process(
        self,
        client_sock: Socket,
        addr: Tuple[str, int],
        lottery_monitor: LotteryMonitor,
    ):
        """
        Run in a separate process: handle all communication with a single client.
        """
        self._logger.info(f"action: client_handler_started | client: {addr}")

        try:
            keep_handling_client = Server.CONTINUE
            while keep_handling_client != Server.STOP:
                try:
                    msg = client_sock.receive_message()
                    self._logger.info(
                        f"action: receive_message | result: success | msg: {msg} | client: {addr}"
                    )
                    keep_handling_client = self.send_message_response(
                        client_sock, msg, lottery_monitor
                    )
                except (ConnectionError, ValueError, OSError) as e:
                    self._logger.error(
                        f"action: receive_message | result: fail | error: {e} | client: {addr}"
                    )
                    break
        finally:
            self._protocol.shutdown_socket(client_sock)
            self._logger.info(f"action: client_handler_stopped | client: {addr}")

    # def __handle_new_connection(self, welcomming_socket: StdSocket) -> None:
    #     """
    #     Accept a new client connection if capacity allows.
    #     Rejects the connection if max agencies already connected.
    #     """
    #     if len(self._clients) >= self._max_agencies:
    #         self._logger.warning(
    #             "action: accept_connections | result: fail | reason: max_clients_reached"
    #         )
    #         # Accept and immediately close the connection
    #         addr, client_socket = welcomming_socket.accept()
    #         self._protocol.shutdown_socket(Socket.__from_existing(client_socket))
    #         return

    #     addr, client_socket = self._protocol.accept_new_connection()
    #     if client_socket:
    #         self._clients.append(client_socket)

    # def __handle_current_connection(
    #     self, client_sock: StdSocket, keep_handling_client: int
    # ) -> int:
    #     """
    #     Handle an incoming message from an existing client connection.
    #     """
    #     if not self._running:
    #         return Server.STOP

    #     # Find the wrapped Socket object for this raw socket
    #     client = next(c for c in self._clients if c.get_socket() is client_sock)

    #     try:
    #         # Decode message from client
    #         msg = client.receive_message()

    #         # Identify agency by its port (temporary ID until bets reveal agency ID)
    #         agencyPort = client_sock.getpeername()[1]
    #         agency = (
    #             self._agency_id_by_port.get(agencyPort)
    #             if self._agency_id_by_port.get(agencyPort)
    #             else agencyPort
    #         )
    #         self._logger.info(
    #             f"action: receive_message | result: success | msg: {msg} | client: {agency}"
    #         )

    #         return self.send_message_response(client, msg)

    #     except (ConnectionError, ValueError, OSError) as e:
    #         # If error occurs, close client connection
    #         if keep_handling_client != Server.CONTINUE_SAFE_TO_END:
    #             self._logger.error(
    #                 f"action: receive_message | result: fail | error: {e}"
    #             )

    #         self._protocol.shutdown_socket(client)
    #         self._clients.remove(client)
    #         return keep_handling_client

    def send_message_response(
        self, client_sock: Socket, msg: Message, lottery_monitor: LotteryMonitor
    ) -> int:
        """
        Dispatch message and send response.
        """
        if isinstance(msg, MsgRegisterBets):
            agencyPort = client_sock.get_port()
            agencyId = msg.get_bets()[0]._agency

            lottery_monitor.set_readiness(agencyPort, Server.AGENCY_SENDING_BETS)
            lottery_monitor.set_agency_id(agencyPort, agencyId)
            self.__process_batch_bet_registration(client_sock, msg, lottery_monitor)
            return Server.CONTINUE

        elif isinstance(msg, MsgAck):
            if lottery_monitor.has_lottery_occurred():
                return Server.CONTINUE_SAFE_TO_END
            return Server.CONTINUE

        elif isinstance(msg, MsgAllBetsSent):
            agencyPort = client_sock.get_port()
            lottery_monitor.set_readiness(agencyPort, Server.AGENCY_READY_FOR_LOTTERY)

            if self.__all_agencies_ready(lottery_monitor):
                # Try to execute lottery (only first process will succeed)
                self.__do_lottery(lottery_monitor)
                # Send winners to this client if they're waiting
                self.__send_winners_to_client(client_sock, lottery_monitor)

            return Server.CONTINUE_SAFE_TO_END

        elif isinstance(msg, MsgRequestWinners):
            agencyPort = client_sock.get_port()
            lottery_monitor.set_readiness(agencyPort, Server.AGENCY_WAITING_FOR_LOTTERY)
            if lottery_monitor.has_lottery_occurred():
                self.__send_winners_to_client(client_sock, lottery_monitor)
                return Server.CONTINUE_SAFE_TO_END
            else:
                agency = lottery_monitor.get_agency_id(agencyPort)
                self._logger.info(
                    f"action: agency_{agency}_waiting | result: in_progress"
                )
            return Server.CONTINUE

        else:
            self._protocol.send_register_bets_failed(
                client_sock, FAILURE_UNKNOWN_MESSAGE
            )
            self._logger.error("action: mensaje_desconocido | result: fail")
            return Server.STOP

    def __send_winners_to_client(
        self, client_sock: Socket, lottery_monitor: LotteryMonitor
    ):
        """
        Send winners to this specific client if they're waiting for them.
        """
        agencyPort = client_sock.get_port()
        current_state = lottery_monitor.get_readiness(agencyPort)

        # Only send winners if the agency is waiting for them
        if current_state == Server.AGENCY_WAITING_FOR_LOTTERY:
            agencyId = lottery_monitor.get_agency_id(agencyPort)

            if agencyId:
                dni_winners = lottery_monitor.get_winners_for_agency(agencyId)
                self._logger.info(
                    f"action: inform_winners | result: success | client: {agencyId}"
                )
                self._protocol.inform_winners(client_sock, dni_winners)

                # Mark agency as having received winners
                lottery_monitor.set_readiness(
                    agencyPort, Server.AGENCY_GOT_LOTTERY_WINNERS
                )
            else:
                self._logger.warning(
                    f"action: inform_winners | result: fail | reason: agency_id_not_found | port: {agencyPort}"
                )

    # def send_message_response(self, client_sock: Socket, msg: Message) -> int:
    #     """
    #     Dispatch message and send response.

    #     - `MsgRegisterBets`: store bets, send OK/Fail → CONTINUE
    #     - `MsgAck`: acknowledge → CONTINUE (if lottery done, may end)
    #     - `MsgAllBetsSent`: mark agency ready → CONTINUE (if all ready, run lottery)
    #     - `MsgRequestWinners`: if lottery done, send winners → CONTINUE_SAFE_TO_END
    #     - Unknown: send failure → STOP
    #     """
    #     if isinstance(msg, MsgRegisterBets):
    #         # Client is sending bets
    #         agencyPort = client_sock.get_port()
    #         self._readiness_status[agencyPort] = Server.AGENCY_SENDING_BETS
    #         self._agency_id_by_port[agencyPort] = msg.get_bets()[0]._agency

    #         self.__process_batch_bet_registration(client_sock, msg)
    #         return Server.CONTINUE

    #     elif isinstance(msg, MsgAck):
    #         # Client acknowledged last message
    #         if self.__lottery_occurred():
    #             return Server.CONTINUE_SAFE_TO_END
    #         return Server.CONTINUE

    #     elif isinstance(msg, MsgAllBetsSent):
    #         # Agency finished sending bets
    #         agencyPort = client_sock.get_port()
    #         self._readiness_status[agencyPort] = Server.AGENCY_READY_FOR_LOTTERY

    #         if self.__all_agencies_ready():
    #             # All agencies ready → compute and send winners
    #             self.__do_lottery()
    #             self.__inform_winners_to_waiting_agencies()
    #             return Server.CONTINUE_SAFE_TO_END

    #         return Server.CONTINUE

    #     elif isinstance(msg, MsgRequestWinners):
    #         # Agency requests winners
    #         agencyPort = client_sock.get_port()
    #         self._readiness_status[agencyPort] = Server.AGENCY_WAITING_FOR_LOTTERY

    #         if self.__lottery_occurred():
    #             # Lottery already done → send winners
    #             self.__inform_winners_to_waiting_agencies()
    #             return Server.CONTINUE_SAFE_TO_END
    #         else:
    #             # Not all agencies ready yet
    #             agency = self._agency_id_by_port.get(agencyPort)
    #             self._logger.info(
    #                 f"action: agency_{agency}_waiting | result: in_progress"
    #             )

    #         return Server.CONTINUE

    #     else:
    #         # Unknown message type → send failure response
    #         self._protocol.send_register_bets_failed(
    #             client_sock, FAILURE_UNKNOWN_MESSAGE
    #         )
    #         self._logger.error("action: mensaje_desconocido | result: fail")
    #         return Server.STOP

    # def __lottery_occurred(self) -> bool:
    #     """Return True if winners have already been computed."""
    #     return len(self._winners) > 0

    # def __all_agencies_ready(self) -> bool:
    #     """
    #     Return True if all agencies are connected and none are still sending bets.
    #     """

    #     # Ensure all expected agencies are connected
    #     are_all_agencies_connected = len(self._clients) == self._max_agencies
    #     if not are_all_agencies_connected:
    #         return False

    #     # Check readiness state of all agencies
    #     for status in self._readiness_status.values():
    #         if status == Server.AGENCY_SENDING_BETS:
    #             return False

    #     return True

    def __all_agencies_ready(self, lottery_monitor: LotteryMonitor) -> bool:
        """
        Return True if all agencies are connected and none are still sending bets.
        """
        return lottery_monitor.all_agencies_ready(
            self._max_agencies, Server.AGENCY_SENDING_BETS
        )

    # def __do_lottery(self):
    #     """
    #     Compute winners and group them by agency.
    #     """
    #     bets: List[Bet] = load_bets()

    #     # Collect all winning bets (agency, dni)
    #     for bet in bets:
    #         if has_won(bet):
    #             self._winners.append((int(bet.agency), int(bet.document)))

    #     # Group winners by agency
    #     for agency, dni in self._winners:
    #         if agency not in self._winners_per_agency:
    #             self._winners_per_agency[agency] = []
    #         self._winners_per_agency[agency].append(dni)

    #     self._logger.info("action: sorteo | result: success")

    def __do_lottery(self, lottery_monitor: LotteryMonitor) -> None:
        """
        Execute the lottery if it hasn't been executed yet.

        Returns:
            bool: True if lottery was executed by this call, False if already executed
        """
        lottery_executed = lottery_monitor.execute_lottery()
        if lottery_executed:
            self._logger.info("action: sorteo | result: success")

    # def __inform_winners_to_waiting_agencies(self):
    #     """
    #     Send winners to each connected agency that is waiting for them.
    #     """

    #     # Send winners to each connected client
    #     for client in self._clients:
    #         agencyPort: int = client.get_port()
    #         if (
    #             self._readiness_status.get(agencyPort)
    #             == Server.AGENCY_WAITING_FOR_LOTTERY
    #         ):
    #             agencyId: Optional[int] = self._agency_id_by_port.get(agencyPort)

    #             if agencyId:
    #                 dni_winners = self._winners_per_agency.get(agencyId, [])
    #                 self._logger.info(
    #                     f"action: inform_winners | result: success | client: {agencyId}"
    #                 )
    #                 self._protocol.inform_winners(client, dni_winners)
    #                 # Mark agency as having received winners
    #                 self._readiness_status[agencyPort] = (
    #                     Server.AGENCY_GOT_LOTTERY_WINNERS
    #                 )

    def __inform_winners_to_waiting_agencies(self, lottery_monitor: LotteryMonitor):
        """
        Send winners to each connected agency that is waiting for them.
        """
        readiness = lottery_monitor.all_readiness()
        for port, state in readiness.items():
            if state == Server.AGENCY_WAITING_FOR_LOTTERY:
                agencyId: Optional[int] = lottery_monitor.get_agency_id(port)
                if agencyId:
                    dni_winners = lottery_monitor.get_winners_for_agency(agencyId)
                    self._logger.info(
                        f"action: inform_winners | result: success | client: {agencyId}"
                    )
                    # NOTE: We don't have the Socket object here anymore,
                    # so in real code you'd need a way to map port → Socket.
                    # For now, assume we can still send via client_sock.
                    # self._protocol.inform_winners(client_sock, dni_winners)
                    lottery_monitor.set_readiness(
                        port, Server.AGENCY_GOT_LOTTERY_WINNERS
                    )

    # def __process_batch_bet_registration(
    #     self, client_sock: Socket, msg: MsgRegisterBets
    # ):
    #     """
    #     Process a batch bet registration request.

    #     Converts the received `StandardBet` objects into domain `Bet`
    #     objects, stores them, and sends either a success or failure
    #     response back to the client.
    #     """
    #     standard_bets: List[StandardBet] = msg.get_bets()

    #     # Attempt to store bets in persistent storage
    #     storing_success: bool = self.__store_bets(standard_bets)

    #     if storing_success:
    #         # Acknowledge success
    #         self._protocol.send_register_bets_ok(client_sock)
    #         self._logger.info(
    #             f"action: apuesta_recibida | result: success | cantidad: {len(standard_bets)}"
    #         )
    #         return

    #     # If storing failed, send failure response
    #     self._protocol.send_register_bets_failed(
    #         client_sock, FAILURE_COULD_NOT_PROCESS_BET
    #     )
    #     self._logger.info(
    #         f"action: apuesta_recibida | result: fail | cantidad: {len(standard_bets)}"
    #     )

    def __process_batch_bet_registration(
        self, client_sock: Socket, msg: MsgRegisterBets, lottery_monitor: LotteryMonitor
    ):
        standard_bets: List[StandardBet] = msg.get_bets()
        storing_success: bool = self.__store_bets(standard_bets, lottery_monitor)
        if storing_success:
            self._protocol.send_register_bets_ok(client_sock)
            self._logger.info(
                f"action: apuesta_recibida | result: success | cantidad: {len(standard_bets)}"
            )
            return
        self._protocol.send_register_bets_failed(
            client_sock, FAILURE_COULD_NOT_PROCESS_BET
        )
        self._logger.info(
            f"action: apuesta_recibida | result: fail | cantidad: {len(standard_bets)}"
        )

    # def __store_bets(self, standard_bets: List[StandardBet]) -> bool:
    #     """
    #     Convert protocol-level bets into domain `Bet` objects and store them.

    #     Returns
    #     -------
    #     bool
    #         True if storing succeeded, False otherwise.
    #     """
    #     bets: List[Bet] = []
    #     for bet in standard_bets:
    #         bets.append(bet.to_utility_bet())

    #     try:
    #         store_bets(bets)
    #         return True
    #     except Exception:
    #         # Any exception during storage is treated as a failure
    #         return False

    def __store_bets(
        self, standard_bets: List[StandardBet], lottery_monitor: LotteryMonitor
    ) -> bool:
        bets: List[Bet] = [bet.to_utility_bet() for bet in standard_bets]
        return lottery_monitor.store_bets(bets)

    # def stop(self) -> None:
    #     """
    #     Stop the server.

    #     Shuts down and closes the listening socket, sets the server
    #     state to stopped, and prevents further connections.
    #     """
    #     self._running = False

    #     if self._stopped:
    #         return

    #     # Close all client sockets
    #     for client_sock in self._clients:
    #         self._protocol.shutdown_socket(client_sock)

    #     self._clients = []

    #     # Close listening socket
    #     self._protocol.shutdown()
    #     self._stopped = True

    def stop(self) -> None:
        self._running = False
        if self._stopped:
            return
        self._protocol.shutdown()
        for p in self._processes:
            p.terminate()
        self._stopped = True
