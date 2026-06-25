"""Ensemble Protocol (ESP) — group collaboration for specialized AI agents."""

from .ensemble import Ensemble, make_envelope
from .lifecycle import LifecycleState
from .models import Addressing, Envelope, EnsembleDoc, Member, Participant, Payload
from .patterns import CoordinationPattern
from .roles import Role

__version__ = "0.1.0"
ESP_VERSION = __version__

__all__ = [
    "ESP_VERSION",
    "Addressing",
    "CoordinationPattern",
    "Ensemble",
    "EnsembleDoc",
    "Envelope",
    "LifecycleState",
    "Member",
    "Participant",
    "Payload",
    "Role",
    "make_envelope",
]