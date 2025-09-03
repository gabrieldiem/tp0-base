from common.utils import Bet
from datetime import date

MSG_TYPE_REGISTER_BET = 1
MSG_TYPE_REGISTER_BET_OK = 2
MSG_TYPE_REGISTER_BET_FAILED = 3

SIZEOF_UINT16 = 2
SIZEOF_UINT32 = 4
SIZEOF_INT64 = 8
SIZEOF_UINT64 = 8

UNKNOWN_BET_INFO = 0

FAILURE_UNKNOWN_MESSAGE = 1

from typing import Literal


class Message:
    """
    Abstract base class for all protocol messages.

    Each message must implement `to_bytes()` to serialize itself into
    the binary TLV format:

        [2 bytes msg_type][4 bytes payload_length][payload...]

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


class MsgRegisterBet(Message):
    """
    Client → Server message: request to register a new bet.

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
        DNI.
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
        self._msg_type = MSG_TYPE_REGISTER_BET
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
        Serialize the message into TLV binary format.
        """
        payload: bytes = b""

        # Agency
        payload += int(self._agency).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )

        # Name
        name_bytes: bytes = self._name.encode(character_encoding)
        payload += len(name_bytes).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )
        payload += name_bytes

        # Surname
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

        # Header
        header: bytes = self._msg_type.to_bytes(
            SIZEOF_UINT16,
            endianness,
        )
        header += len(payload).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )

        return header + payload

    def get_bet(self) -> Bet:
        """
        Convert this message into a domain `Bet` object.

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

    def __str__(self) -> str:
        return (
            f"MsgRegisterBet(name={self._name}, surname={self._surname}, "
            f"dni={self._dni}, birthdate={self._birthdate}, number={self._number})"
        )


class MsgRegisterBetOk(Message):
    """
    Server → Client message: bet successfully registered.

    Payload format:
        [4 bytes dni]
        [4 bytes number]

    Attributes
    ----------
    _dni : int
        DNI of the bettor.
    _number : int
        Bet number confirmed by the server.
    """

    def __init__(self, dni: int, number: int):
        self._msg_type = MSG_TYPE_REGISTER_BET_OK
        self._dni = dni
        self._number = number

    def to_bytes(
        self, character_encoding: str, endianness: Literal["big", "little"]
    ) -> bytes:
        """
        Serialize the message into TLV binary format.
        """
        payload: bytes = b""
        payload += int(self._dni).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )
        payload += int(self._number).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )

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
        return f"MsgRegisterBetOk(dni={self._dni}, number={self._number})"


class MsgRegisterBetFailed(Message):
    """
    Server → Client message: bet registration failed.

    Payload format:
        [4 bytes dni]
        [4 bytes number]
        [2 bytes error_code]

    Attributes
    ----------
    _dni : int
        DNI of the bettor. May be invalid depending on the error
    _number : int
        Bet number attempted. May be invalid depending on the error
    _error_code : int
        Error code indicating reason for failure.
    """

    def __init__(self, dni: int, number: int, error_code: int):
        self._msg_type = MSG_TYPE_REGISTER_BET_FAILED
        self._dni = dni
        self._number = number
        self._error_code = error_code

    def to_bytes(
        self, character_encoding: str, endianness: Literal["big", "little"]
    ) -> bytes:
        """
        Serialize the message into TLV binary format.
        """
        payload: bytes = b""
        payload += int(self._dni).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )
        payload += int(self._number).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )
        payload += int(self._error_code).to_bytes(
            SIZEOF_UINT16,
            endianness,
        )

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
        return (
            f"MsgRegisterBetFailed(dni={self._dni}, number={self._number}, "
            f"error_code={self._error_code})"
        )
