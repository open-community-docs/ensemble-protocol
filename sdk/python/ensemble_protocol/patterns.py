from enum import Enum


class CoordinationPattern(str, Enum):
    BROADCAST = "broadcast"
    UNICAST = "unicast"
    REQUEST_ANY = "request_any"
    REQUEST_ALL = "request_all"
    CONTRACT_NET = "contract_net"
    BLACKBOARD_POST = "blackboard_post"
    HANDOFF = "handoff"