from logging import Logger
from common.protocol import Protocol
from common.socket import Socket
from typing import Tuple, List
from common.utils import Bet
from common.lottery_monitor import LotteryMonitor
from multiprocessing import Process, Event

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
        self._shutdown_event = Event()

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
                        target=self.__handle_client_process,
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

    def __handle_client_process(
        self,
        client_sock: Socket,
        addr: Tuple[str, int],
        lottery_monitor: LotteryMonitor,
    ):
        """
        Run in a separate process: handle all communication with a single client.
        """
        self._logger.info(f"action: client_handler_started | result: success | client: {addr[0]}:{addr[1]}")
        
        try:
            keep_handling_client = Server.CONTINUE
            while keep_handling_client != Server.STOP and not self._shutdown_event.is_set():
                try:
                    msg = client_sock.receive_message()
                    self._logger.info(
                        f"action: receive_message | result: success | msg: {msg} | client: {addr[0]}:{addr[1]}"
                    )
                    keep_handling_client = self.__send_message_response(
                        client_sock, msg, lottery_monitor
                    )

                    # After processing message, check if we should wait for lottery and send winners
                    if keep_handling_client == Server.CONTINUE:
                        agencyPort = client_sock.get_port()
                        current_state = lottery_monitor.get_readiness(agencyPort)

                        # If this client is waiting for lottery, wait for completion and send winners
                        if current_state == Server.AGENCY_WAITING_FOR_LOTTERY:
                            self._logger.info(
                                f"action: waiting_for_lottery | client: {addr[0]}:{addr[1]}"
                            )

                            # Wait for lottery to complete (with timeout to avoid infinite wait)
                            if lottery_monitor.wait_for_lottery_completion():
                                self.__send_winners_to_client(
                                    client_sock, lottery_monitor
                                )
                                keep_handling_client = Server.CONTINUE_SAFE_TO_END
                            else:
                                self._logger.error(
                                    f"action: lottery_timeout | client: {addr[0]}:{addr[1]}"
                                )
                                keep_handling_client = Server.STOP

                except (ConnectionError, ValueError, OSError) as e:
                    if keep_handling_client != Server.CONTINUE_SAFE_TO_END and not self._shutdown_event.is_set():
                        self._logger.error(
                            f"action: receive_message | result: fail | error: {e} | client: {addr[0]}:{addr[1]}"
                        )
                    break
        finally:
            self._protocol.shutdown_socket(client_sock)
            self._logger.info(f"action: client_handler_stopped | client: {addr[0]}:{addr[1]}")

    def __send_message_response(
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
                lottery_executed = self.__do_lottery(lottery_monitor)
                if lottery_executed:
                    # This process executed the lottery, send winners immediately
                    self.__send_winners_to_client(client_sock, lottery_monitor)
                    return Server.CONTINUE_SAFE_TO_END

            return Server.CONTINUE_SAFE_TO_END

        elif isinstance(msg, MsgRequestWinners):
            agencyPort = client_sock.get_port()
            lottery_monitor.set_readiness(agencyPort, Server.AGENCY_WAITING_FOR_LOTTERY)

            if lottery_monitor.has_lottery_occurred():
                # Lottery already completed, send winners immediately
                self.__send_winners_to_client(client_sock, lottery_monitor)
                return Server.CONTINUE_SAFE_TO_END
            else:
                # Lottery not complete yet, will wait in main loop
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

    def __all_agencies_ready(self, lottery_monitor: LotteryMonitor) -> bool:
        """
        Return True if all agencies are connected and none are still sending bets.
        """
        return lottery_monitor.all_agencies_ready(
            self._max_agencies, Server.AGENCY_SENDING_BETS
        )

    def __do_lottery(self, lottery_monitor: LotteryMonitor) -> None:
        """
        Execute the lottery if it hasn't been executed yet.

        Returns:
            bool: True if lottery was executed by this call, False if already executed
        """
        lottery_executed = lottery_monitor.execute_lottery()
        if lottery_executed:
            self._logger.info("action: sorteo | result: success")

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

    def __store_bets(
        self, standard_bets: List[StandardBet], lottery_monitor: LotteryMonitor
    ) -> bool:
        bets: List[Bet] = [bet.to_utility_bet() for bet in standard_bets]
        return lottery_monitor.store_bets(bets)


    def stop(self) -> None:
        self._running = False
        if self._stopped:
            return
        
        # Signal all child processes to shutdown gracefully
        self._shutdown_event.set()
        
        self._protocol.shutdown()
        
        # Give processes time to shutdown gracefully
        for p in self._processes:
            p.join(timeout=5.0)  # Wait up to 5 seconds
            if p.is_alive():
                self._logger.warning(f"Force terminating process {p.pid}")
                p.terminate()
                p.join()
        
        self._stopped = True
