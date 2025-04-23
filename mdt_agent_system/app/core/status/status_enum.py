from enum import Enum

class Status(Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    DONE = "DONE"
    ERROR = "ERROR"
    WAITING = "WAITING" 