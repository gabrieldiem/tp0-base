from multiprocessing import Manager, Lock, Event
from typing import Dict, List, Tuple
from common.utils import Bet, store_bets, load_bets, has_won


class LotteryMonitor:
    def __init__(self):
        manager = Manager()
        self._lock = Lock()

        # Manager-backed shared objects
        self._readiness_status = manager.dict()  # port → state
        self._agency_id_by_port = manager.dict()  # port → agencyId
        self._winners = manager.list()  # list of (agency, dni)
        self._winners_per_agency = manager.dict()  # agency → list of dni
        self._lottery_executed = manager.Value("b", False)  # boolean flag

        # Event to notify all processes when lottery is complete
        self._lottery_complete_event = Event()

    # -------------------------
    # Readiness state
    # -------------------------
    def set_readiness(self, port: int, state: int):
        with self._lock:
            self._readiness_status[port] = state

    def get_readiness(self, port: int) -> int:
        with self._lock:
            return self._readiness_status.get(port, None)

    def all_readiness(self) -> Dict[int, int]:
        with self._lock:
            return dict(self._readiness_status)

    def count_connected_agencies(self) -> int:
        """
        Return the number of agencies that have connected (have a readiness state).
        """
        with self._lock:
            return len(self._readiness_status)

    def all_agencies_ready(self, max_agencies: int, sending_bets_state: int) -> bool:
        """
        Return True if all expected agencies are connected and none are still sending bets.

        Args:
            max_agencies: Expected number of agencies
            sending_bets_state: The state value that indicates an agency is still sending bets

        Returns:
            bool: True if all agencies are ready for lottery
        """
        with self._lock:
            # Check if all expected agencies are connected
            if len(self._readiness_status) < max_agencies:
                return False

            # Check if any agency is still sending bets
            for status in self._readiness_status.values():
                if status == sending_bets_state:
                    return False

            return True

    # -------------------------
    # Agency mapping
    # -------------------------
    def set_agency_id(self, port: int, agency_id: int):
        with self._lock:
            self._agency_id_by_port[port] = agency_id

    def get_agency_id(self, port: int) -> int:
        with self._lock:
            return self._agency_id_by_port.get(port, None)

    # -------------------------
    # Lottery execution and waiting
    # -------------------------
    def execute_lottery(self) -> bool:
        """
        Execute the lottery if it hasn't been executed yet.

        Returns:
            bool: True if lottery was executed by this call, False if already executed
        """
        with self._lock:
            # Check if lottery was already executed
            if self._lottery_executed.value:
                return False

            # Mark as executed first to prevent race conditions
            self._lottery_executed.value = True

            # Load bets and compute winners
            bets: List[Bet] = load_bets()
            for bet in bets:
                if has_won(bet):
                    agency = int(bet.agency)
                    dni = int(bet.document)

                    # Add to winners list
                    self._winners.append((agency, dni))

                    # Group by agency
                    if agency not in self._winners_per_agency.keys():
                        self._winners_per_agency[agency] = []

                    self._winners_per_agency[agency] = self._winners_per_agency[
                        agency
                    ] + [dni]

        # Set the event to wake up all waiting processes (outside the lock)
        self._lottery_complete_event.set()
        return True

    def wait_for_lottery_completion(self) -> bool:
        """
        Wait for the lottery to be completed.

        Args:
            timeout: Maximum time to wait in seconds. None means wait indefinitely.

        Returns:
            bool: True if lottery completed, False if timeout occurred
        """
        return self._lottery_complete_event.wait()

    def is_lottery_complete(self) -> bool:
        """
        Check if the lottery completion event is set (non-blocking).
        """
        return self._lottery_complete_event.is_set()

    # -------------------------
    # Winners
    # -------------------------
    def add_winner(self, agency: int, dni: int):
        """
        Manually add a winner (for testing or special cases).
        """
        with self._lock:
            self._winners.append((agency, dni))
            if agency not in self._winners_per_agency:
                self._winners_per_agency[agency] = []
            self._winners_per_agency[agency].append(dni)

    def get_winners(self) -> List[Tuple[int, int]]:
        with self._lock:
            return list(self._winners)

    def get_winners_for_agency(self, agency: int) -> List[int]:
        with self._lock:
            return list(self._winners_per_agency.get(agency, []))

    def has_lottery_occurred(self) -> bool:
        with self._lock:
            return self._lottery_executed.value

    # -------------------------
    # Bet storage (process-safe)
    # -------------------------
    def store_bets(self, bets: List[Bet]) -> bool:
        """
        Store bets in a process-safe manner.

        Args:
            bets: List of Bet objects to store

        Returns:
            bool: True if storing succeeded, False otherwise
        """
        with self._lock:
            try:
                store_bets(bets)
                return True
            except Exception:
                return False
