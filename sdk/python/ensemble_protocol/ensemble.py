from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .ids import make_ensemble_id
from .lifecycle import LifecycleState
from .models import (
    ESP_VERSION,
    Addressing,
    EnsembleDoc,
    Envelope,
    Member,
    Participant,
    Payload,
)
from .patterns import CoordinationPattern
from .roles import Role


class Ensemble:
    """In-memory ensemble with lifecycle and member resolution."""

    def __init__(self, doc: EnsembleDoc) -> None:
        self._doc = doc

    @property
    def doc(self) -> EnsembleDoc:
        return self._doc

    @property
    def ensemble_id(self) -> str:
        return self._doc.ensemble_id

    @property
    def state(self) -> LifecycleState:
        return self._doc.state

    @classmethod
    def create(
        cls,
        *,
        coordinator: str,
        namespace: str,
        name: str,
        members: list[Member],
        metadata: dict[str, Any] | None = None,
        activate: bool = True,
    ) -> Ensemble:
        ensemble_id = make_ensemble_id(namespace, name)
        all_members = list(members)
        if not any(m.agent_ref == coordinator for m in all_members):
            all_members.insert(
                0,
                Member(
                    agent_ref=coordinator,
                    role=Role.COORDINATOR,
                    permissions=["coordinate", "read_blackboard", "post_artifacts"],
                ),
            )
        doc = EnsembleDoc(
            ensemble_id=ensemble_id,
            state=LifecycleState.ACTIVE if activate else LifecycleState.PROPOSED,
            coordinator=coordinator,
            members=all_members,
            metadata=metadata or {},
        )
        return cls(doc)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Ensemble:
        return cls(EnsembleDoc.model_validate(data))

    def transition(self, target: LifecycleState) -> None:
        if not self._doc.state.can_transition_to(target):
            raise ValueError(
                f"cannot transition from {self._doc.state.value} to {target.value}"
            )
        self._doc.state = target

    def resolve(self, selector: str) -> list[Member]:
        """Resolve an addressing selector to member records."""
        if selector == "all:members" or selector == "all:all":
            return list(self._doc.members)

        kind, _, value = selector.partition(":")
        if not value:
            raise ValueError(f"invalid selector: {selector!r}")

        if kind == "role":
            return [m for m in self._doc.members if m.role.value == value]
        if kind == "agent":
            return [m for m in self._doc.members if m.agent_ref == value]
        if kind == "skill":
            return [m for m in self._doc.members if value in m.skills]
        if kind == "all":
            return list(self._doc.members)

        raise ValueError(f"unknown selector kind: {kind!r}")

    def resolve_agent_refs(self, selector: str, *, exclude_self: str | None = None) -> list[str]:
        refs = [m.agent_ref for m in self.resolve(selector)]
        if exclude_self:
            refs = [r for r in refs if r != exclude_self]
        return refs

    def make_envelope(
        self,
        pattern: CoordinationPattern,
        *,
        to: Addressing,
        payload: Payload | dict[str, Any],
        from_agent: str | None = None,
        from_role: Role = Role.COORDINATOR,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Envelope:
        if self._doc.state not in (LifecycleState.ACTIVE, LifecycleState.CLOSING):
            raise RuntimeError(f"ensemble not active: {self._doc.state.value}")

        if isinstance(payload, dict):
            payload = Payload.model_validate(payload)

        return Envelope(
            ensemble_id=self.ensemble_id,
            pattern=pattern,
            **{
                "from": Participant(
                    agent_ref=from_agent or self._doc.coordinator,
                    role=from_role,
                )
            },
            to=to,
            correlation_id=correlation_id or f"msg-{uuid.uuid4().hex[:12]}",
            causation_id=causation_id,
            payload=payload,
            metadata=metadata or {},
        )


def make_envelope(
    ensemble: Ensemble | EnsembleDoc | str,
    pattern: CoordinationPattern,
    *,
    text: str | None = None,
    intent: str | None = None,
    to_selector: str = "role:specialist",
    from_agent: str | None = None,
    correlation_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Envelope:
    """Convenience helper for quick envelope construction."""
    if isinstance(ensemble, str):
        raise TypeError("pass an Ensemble instance, not a bare ensemble_id string")
    ens = ensemble if isinstance(ensemble, Ensemble) else Ensemble(ensemble)
    payload = Payload(intent=intent, text=text)
    if text and not intent:
        payload.intent = "message"
    return ens.make_envelope(
        pattern,
        to=Addressing(selector=to_selector),
        payload=payload,
        from_agent=from_agent,
        correlation_id=correlation_id,
        metadata=metadata,
    )