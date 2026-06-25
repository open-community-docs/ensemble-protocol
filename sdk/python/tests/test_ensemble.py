import pytest

from ensemble_protocol import CoordinationPattern, Ensemble, Member, Role
from ensemble_protocol.lifecycle import LifecycleState
from ensemble_protocol.models import Addressing, Payload


def test_create_ensemble_adds_coordinator():
    ens = Ensemble.create(
        coordinator="financial-agent",
        namespace="bknight.dev",
        name="test-flow",
        members=[
            Member(agent_ref="document-agent", role=Role.SPECIALIST, skills=["document.ingest"]),
        ],
    )
    assert ens.ensemble_id == "ens://bknight.dev/test-flow"
    assert ens.state == LifecycleState.ACTIVE
    refs = {m.agent_ref for m in ens.doc.members}
    assert refs == {"financial-agent", "document-agent"}


def test_resolve_by_role_and_skill():
    ens = Ensemble.create(
        coordinator="financial-agent",
        namespace="bknight.dev",
        name="test-flow",
        members=[
            Member(agent_ref="document-agent", role=Role.SPECIALIST, skills=["document.ingest"]),
            Member(agent_ref="email-agent", role=Role.SPECIALIST, skills=["send_document"]),
        ],
    )
    specialists = ens.resolve("role:specialist")
    assert len(specialists) == 2
    ingest = ens.resolve_agent_refs("skill:document.ingest")
    assert ingest == ["document-agent"]


def test_lifecycle_transitions():
    ens = Ensemble.create(
        coordinator="a",
        namespace="test",
        name="lc",
        members=[],
        activate=False,
    )
    assert ens.state == LifecycleState.PROPOSED
    ens.transition(LifecycleState.ACTIVE)
    ens.transition(LifecycleState.SUSPENDED)
    ens.transition(LifecycleState.ACTIVE)
    ens.transition(LifecycleState.CLOSING)
    ens.transition(LifecycleState.CLOSED)
    with pytest.raises(ValueError):
        ens.transition(LifecycleState.ACTIVE)


def test_make_envelope():
    ens = Ensemble.create(
        coordinator="financial-agent",
        namespace="bknight.dev",
        name="test-flow",
        members=[
            Member(agent_ref="email-agent", role=Role.SPECIALIST),
        ],
    )
    env = ens.make_envelope(
        CoordinationPattern.BROADCAST,
        to=Addressing(selector="role:specialist"),
        payload=Payload(intent="deliver", text="hi"),
    )
    assert env.ensemble_id == "ens://bknight.dev/test-flow"
    assert env.pattern == CoordinationPattern.BROADCAST
    assert env.payload.text == "hi"