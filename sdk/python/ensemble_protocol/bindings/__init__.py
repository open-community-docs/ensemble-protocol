"""Transport bindings for ESP envelopes."""

try:
    from .a2a_relay import A2ARelayBinding
except ImportError:  # httpx / a2a-sdk optional
    A2ARelayBinding = None  # type: ignore[misc, assignment]

__all__ = ["A2ARelayBinding"]