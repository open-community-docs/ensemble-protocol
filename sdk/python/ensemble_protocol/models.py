from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from .lifecycle import LifecycleState
from .patterns import CoordinationPattern
from .roles import Role

ESP_VERSION = "0.1.0"


class Member(BaseModel):
    agent_ref: str
    role: Role
    skills: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    accepted_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Participant(BaseModel):
    agent_ref: str
    role: Role


class Addressing(BaseModel):
    selector: str

    @classmethod
    def all_members(cls) -> Addressing:
        return cls(selector="all:members")

    @classmethod
    def role(cls, role: Role | str) -> Addressing:
        value = role.value if isinstance(role, Role) else role
        return cls(selector=f"role:{value}")

    @classmethod
    def agent(cls, agent_ref: str) -> Addressing:
        return cls(selector=f"agent:{agent_ref}")

    @classmethod
    def skill(cls, skill: str) -> Addressing:
        return cls(selector=f"skill:{skill}")


class Payload(BaseModel):
    intent: str | None = None
    phase: str | None = None
    text: str | None = None
    a2a_message: dict[str, Any] | None = None
    artifact: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


class Envelope(BaseModel):
    esp_version: str = ESP_VERSION
    ensemble_id: str
    pattern: CoordinationPattern
    from_: Participant = Field(alias="from")
    to: Addressing
    correlation_id: str
    causation_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Payload
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

    def to_dict(self) -> dict[str, Any]:
        data = self.model_dump(by_alias=True, mode="json")
        return data


class EnsembleDoc(BaseModel):
    esp_version: str = ESP_VERSION
    ensemble_id: str
    state: LifecycleState
    coordinator: str
    members: list[Member]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")