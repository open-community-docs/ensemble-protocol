from enum import Enum


class LifecycleState(str, Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSING = "closing"
    CLOSED = "closed"

    def can_transition_to(self, target: "LifecycleState") -> bool:
        allowed: dict[LifecycleState, set[LifecycleState]] = {
            LifecycleState.PROPOSED: {LifecycleState.ACTIVE, LifecycleState.CLOSED},
            LifecycleState.ACTIVE: {
                LifecycleState.SUSPENDED,
                LifecycleState.CLOSING,
                LifecycleState.CLOSED,
            },
            LifecycleState.SUSPENDED: {LifecycleState.ACTIVE, LifecycleState.CLOSED},
            LifecycleState.CLOSING: {LifecycleState.CLOSED},
            LifecycleState.CLOSED: set(),
        }
        return target in allowed.get(self, set())