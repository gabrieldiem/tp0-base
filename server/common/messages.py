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
    # character_encoding "utf-8"
    def to_bytes(
        self, character_encoding: str, endianness: Literal["big", "little"]
    ) -> bytes:
        raise NotImplementedError()


class MsgRegisterBet(Message):
    def __init__(
        self,
        agency: int,
        name: str,
        surname: str,
        dni: int,
        birthdate: int,
        number: int,
    ):
        self.msg_type = MSG_TYPE_REGISTER_BET
        self.agency = agency
        self.name = name
        self.surname = surname
        self.dni = dni
        self.birthdate = birthdate  # unix timestamp
        self.number = number

    def to_bytes(
        self, character_encoding: str, endianness: Literal["big", "little"]
    ) -> bytes:
        payload = b""

        # Agency
        payload += int(self.agency).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )

        # Name
        name_bytes = self.name.encode(character_encoding)
        payload += len(name_bytes).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )
        payload += name_bytes

        # Surname
        surname_bytes = self.surname.encode(character_encoding)
        payload += len(surname_bytes).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )
        payload += surname_bytes

        # Dni
        payload += int(self.dni).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )

        # Birthdate (unix timestamp, int64)
        payload += int(self.birthdate).to_bytes(SIZEOF_INT64, endianness, signed=True)

        # Number
        payload += int(self.number).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )

        # Header
        header = self.msg_type.to_bytes(
            SIZEOF_UINT16,
            endianness,
        )
        header += len(payload).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )

        return header + payload

    def get_bet(self) -> Bet:
        """Convert MsgRegisterBet into a Bet domain object."""
        # Convert Unix timestamp → ISO date string
        birthdate_str = date.fromtimestamp(self.birthdate).isoformat()

        return Bet(
            agency=str(self.agency),
            first_name=self.name,
            last_name=self.surname,
            document=str(self.dni),
            birthdate=birthdate_str,
            number=str(self.number),
        )

    def __str__(self) -> str:
        return (
            f"MsgRegisterBet(name={self.name}, surname={self.surname}, "
            f"dni={self.dni}, birthdate={self.birthdate}, number={self.number})"
        )


class MsgRegisterBetOk(Message):
    def __init__(self, dni: int, number: int):
        self.msg_type = MSG_TYPE_REGISTER_BET_OK
        self.dni = dni
        self.number = number

    def to_bytes(
        self, character_encoding: str, endianness: Literal["big", "little"]
    ) -> bytes:
        payload = b""
        payload += int(self.dni).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )
        payload += int(self.number).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )

        header = self.msg_type.to_bytes(
            SIZEOF_UINT16,
            endianness,
        )
        header += len(payload).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )
        return header + payload

    def __str__(self) -> str:
        return f"MsgRegisterBetOk(dni={self.dni}, number={self.number})"


class MsgRegisterBetFailed(Message):
    def __init__(self, dni: int, number: int, error_code: int):
        self.msg_type = MSG_TYPE_REGISTER_BET_FAILED
        self.dni = dni
        self.number = number
        self.error_code = error_code

    def to_bytes(
        self, character_encoding: str, endianness: Literal["big", "little"]
    ) -> bytes:
        payload = b""
        payload += int(self.dni).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )
        payload += int(self.number).to_bytes(
            SIZEOF_UINT32,
            endianness,
        )
        payload += int(self.error_code).to_bytes(
            SIZEOF_UINT16,
            endianness,
        )

        header = self.msg_type.to_bytes(
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
            f"MsgRegisterBetFailed(dni={self.dni}, number={self.number}, "
            f"error_code={self.error_code})"
        )
