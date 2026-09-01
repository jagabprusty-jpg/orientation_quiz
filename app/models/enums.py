from enum import Enum


class RoundStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ENDED = "ended"


class OptionEnum(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
