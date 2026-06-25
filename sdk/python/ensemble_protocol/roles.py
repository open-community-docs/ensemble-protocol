from enum import Enum


class Role(str, Enum):
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    OBSERVER = "observer"
    BROKER = "broker"