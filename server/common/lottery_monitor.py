from multiprocessing import Manager, Lock, Event
from typing import List
from common.utils import Bet, store_bets, load_bets, has_won


class LotteryMonitor:
    """
    Shared monitor for coordinating state between multiple server processes.

    Responsibilities:
    - Track readiness state of each connected agency.
    - Map client ports to agency IDs.
    - Store and retrieve winners in a process-safe way.
    - Ensure the lottery is executed only once.
    - Notify all waiting processes when the lottery is complete.
    - Provide process-safe bet storage.
    """

    BOOLEAN_TYPECODE = "b"

    def __init__(self):
        self._manager = Manager()
        self._lock = Lock()

        # Manager-backed shared objects (safe across processes)
        self._readiness_status = self._manager.dict()  # address → state
        self._agency_id_by_address = self._manager.dict()  # address → agencyId
        self._winners = self._manager.list()  # list of (agency, dni)
        self._winners_per_agency = self._manager.dict()  # agency → list of dni
        self._lottery_executed = self._manager.Value(
            LotteryMonitor.BOOLEAN_TYPECODE, False
        )  # boolean flag

        # Event used to notify all processes when the lottery is complete
        self._lottery_complete_event = Event()

    def set_readiness(self, address: str, state: int):
        """
        Set the readiness state for a given client address (ip:port).
        """
        with self._lock:
            self._readiness_status[address] = state

    def get_readiness(self, address: str) -> int:
        """
        Get the readiness state for a given client address (ip:port).
        """
        with self._lock:
            return self._readiness_status.get(address, None)

    def all_agencies_ready(self, max_agencies: int, sending_bets_state: int) -> bool:
        """
        Return True if all expected agencies are connected and none are still sending bets.

        Args:
            max_agencies: Expected number of agencies.
            sending_bets_state: The state value that indicates an agency is still sending bets.

        Returns:
            bool: True if all agencies are ready for the lottery.
        """
        with self._lock:
            # Ensure all expected agencies are connected
            if len(self._readiness_status) < max_agencies:
                return False

            # Ensure no agency is still sending bets
            for status in self._readiness_status.values():
                if status == sending_bets_state:
                    return False

            return True

    def set_agency_id(self, address: str, agency_id: int):
        """
        Associate a client address (ip:port) with an agency ID.
        """
        with self._lock:
            self._agency_id_by_address[address] = agency_id

    def get_agency_id(self, address: str) -> int:
        """
        Retrieve the agency ID associated with a client address (ip:port).
        """
        with self._lock:
            return self._agency_id_by_address.get(address, None)

    def execute_lottery(self) -> bool:
        """
        Execute the lottery if it hasn't been executed yet.

        Returns:
            bool: True if lottery was executed by this call,
                  False if it was already executed.
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
        Block until the lottery is completed.

        Returns:
            bool: True if lottery completed, False if timeout occurred.
        """
        return self._lottery_complete_event.wait()

    def get_winners_for_agency(self, agency: int) -> List[int]:
        """
        Return the list of winning DNIs for a given agency.
        """
        with self._lock:
            return list(self._winners_per_agency.get(agency, []))

    def has_lottery_occurred(self) -> bool:
        """
        Return True if the lottery has already been executed.
        """
        with self._lock:
            return self._lottery_executed.value

    def store_bets(self, bets: List[Bet]) -> bool:
        """
        Store bets in a process-safe manner.

        Args:
            bets: List of Bet objects to store.

        Returns:
            bool: True if storing succeeded, False otherwise.
        """
        with self._lock:
            try:
                store_bets(bets)
                return True
            except Exception:
                return False

    def shutdown(self):
        self._manager.shutdown()
