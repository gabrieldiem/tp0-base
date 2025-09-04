from common.utils import Bet
from datetime import date
from typing import Literal, List

# Message type identifiers
MSG_TYPE_REGISTER_BETS = 1
MSG_TYPE_REGISTER_BET_OK = 2
MSG_TYPE_REGISTER_BET_FAILED = 3
MSG_TYPE_ACK = 4

# Sizes of primitive types in bytes
SIZEOF_UINT16 = 2
SIZEOF_UINT32 = 4
SIZEOF_INT64 = 8
SIZEOF_UINT64 = 8

# Failure codes
FAILURE_UNKNOWN_MESSAGE = 1
FAILURE_COULD_NOT_PROCESS_BET = 2


class Message:
    """
    Abstract base class for all protocol messages.

    Each message must implement `to_bytes()` to serialize itself into
    the binary format defined by the protocol.

    Parameters
    ----------
    character_encoding : str
        Encoding used for string fields (e.g. "utf-8").
    endianness : Literal["big", "little"]
        Byte order for integer encoding.
    """

    def to_bytes(
        self, character_encoding: str, endianness: Literal["big", "little"]
    ) -> bytes:
        raise NotImplementedError()


class StandardBet:
    """
    Client → Server payload: a single bet to be registered.

    This is not a top-level message, but a component of
    `MsgRegisterBets`.

    Payload format:
        [4 bytes agency]
        [4 bytes name_length][name_bytes]
        [4 bytes surname_length][surname_bytes]
        [4 bytes dni]
        [8 bytes birthdate_unix_timestamp]
        [4 bytes number]

    Attributes
    ----------
    _agency : int
        Agency identifier.
    _name : str
        First name of the bettor.
    _surname : str
        Last name of the bettor.
    _dni : int
        DNI (document number).
    _birthdate : int
        Birthdate as a Unix timestamp (seconds since epoch).
    _number : int
        Bet number.
    """

    def __init__(
        self,
        agency: int,
        name: str,
        surname: str,
        dni: int,
        birthdate: int,
        number: int,
    ):
        self._agency = agency
        self._name = name
        self._surname = surname
        self._dni = dni
        self._birthdate = birthdate
        self._number = number

    def to_bytes(
        self, character_encoding: str, endianness: Literal["big", "little"]
    ) -> bytes:
        """
        Serialize this bet into binary format.
        """
        payload: bytes = b""

        # Agency
        payload += int(self._agency).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )

        # Name (length + bytes)
        name_bytes: bytes = self._name.encode(character_encoding)
        payload += len(name_bytes).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )
        payload += name_bytes

        # Surname (length + bytes)
        surname_bytes: bytes = self._surname.encode(character_encoding)
        payload += len(surname_bytes).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )
        payload += surname_bytes

        # Dni
        payload += int(self._dni).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )

        # Birthdate (unix timestamp, int64)
        payload += int(self._birthdate).to_bytes(SIZEOF_INT64, endianness, signed=True)

        # Number
        payload += int(self._number).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )

        # Prepend payload length (so server knows how many bytes to read)
        header: bytes = len(payload).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )

        return header + payload

    def to_utility_bet(self) -> Bet:
        """
        Convert this protocol-level bet into a domain `Bet` object.

        Returns
        -------
        Bet
            A domain-level Bet with proper types (date, strings, ints).
        """
        birthdate_str: str = date.fromtimestamp(self._birthdate).isoformat()

        return Bet(
            agency=str(self._agency),
            first_name=self._name,
            last_name=self._surname,
            document=str(self._dni),
            birthdate=birthdate_str,
            number=str(self._number),
        )


class MsgRegisterBets(Message):
    """
    Client → Server message: register one or more bets.

    Payload format:
        [2 bytes msg_type]
        [4 bytes number_of_bets]
        For each bet:
            [4 bytes bet_length][bet_bytes]
    """

    def __init__(self, bets: List[StandardBet]):
        self._msg_type = MSG_TYPE_REGISTER_BETS
        self._number_of_bets = len(bets)
        self._bets = bets

    def to_bytes(
        self, character_encoding: str, endianness: Literal["big", "little"]
    ) -> bytes:
        """
        Serialize the message into binary format.
        """
        payload: bytes = b""
        for bet in self._bets:
            payload += bet.to_bytes(character_encoding, endianness)

        # Header: msg_type + number_of_bets
        header: bytes = self._msg_type.to_bytes(
            SIZEOF_UINT16,
            endianness,
        )
        header += self._number_of_bets.to_bytes(
            SIZEOF_UINT32,
            endianness,
        )
        return header + payload

    def __str__(self) -> str:
        return f"MsgRegisterBets(number_of_bets={self._number_of_bets}, _bets=...)"

    def get_bets(self) -> List[StandardBet]:
        """
        Return the list of bets contained in this message.
        """
        return self._bets


class MsgRegisterBetOk(Message):
    """
    Server → Client message: bet(s) successfully registered.

    Payload format:
        [2 bytes msg_type]
    """

    def __init__(self):
        self._msg_type = MSG_TYPE_REGISTER_BET_OK

    def to_bytes(
        self, character_encoding: str, endianness: Literal["big", "little"]
    ) -> bytes:
        """
        Serialize the message into binary format.
        """
        header: bytes = self._msg_type.to_bytes(
            SIZEOF_UINT16,
            endianness,
        )
        return header

    def __str__(self) -> str:
        return f"MsgRegisterBetOk()"


"""
    Client → Server message: message received confirmation

    Payload format:
        [2 bytes msg_type]
    """


class MsgAck(Message):
    def __init__(self):
        self._msg_type = MSG_TYPE_ACK

    def to_bytes(
        self, character_encoding: str, endianness: Literal["big", "little"]
    ) -> bytes:
        """
        Serialize the message into binary format.
        """
        header: bytes = self._msg_type.to_bytes(
            SIZEOF_UINT16,
            endianness,
        )
        return header

    def __str__(self) -> str:
        return f"MsgAck()"


class MsgRegisterBetFailed(Message):
    """
    Server → Client message: bet registration failed.

    Payload format:
        [2 bytes msg_type]
        [4 bytes payload_length]
        [2 bytes error_code]

    Attributes
    ----------
    _error_code : int
        Error code indicating reason for failure.
    """

    def __init__(self, error_code: int):
        self._msg_type = MSG_TYPE_REGISTER_BET_FAILED
        self._error_code = error_code

    def to_bytes(
        self, character_encoding: str, endianness: Literal["big", "little"]
    ) -> bytes:
        """
        Serialize the message into binary format.
        """
        payload: bytes = b""
        payload += int(self._error_code).to_bytes(
            SIZEOF_UINT16,
            endianness,
        )

        # Header: msg_type + payload_length
        header: bytes = self._msg_type.to_bytes(
            SIZEOF_UINT16,
            endianness,
        )
        header += len(payload).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )
        return header + payload

    def __str__(self) -> str:
        return f"MsgRegisterBetFailed(error_code={self._error_code})"
