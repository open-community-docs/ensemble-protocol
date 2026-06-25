# Ensemble Protocol (ESP)

Open protocol for **group collaboration among specialized, independently-owned AI agents**.

ESP sits between transport (SLIM, HTTP relays) and application semantics (A2A tasks, MCP tools). It defines who participates in a collaboration, what role each agent plays, how messages fan out, and when the collaboration ends — without replacing A2A or SLIM.

## Why ESP exists

| Layer | Examples | Group semantics? |
|-------|----------|------------------|
| Tool access | MCP | No (1:1) |
| Pairwise delegation | A2A | Correlation only (`contextId`) |
| Transport | SLIM, NATS | Pub/sub pipes, not coordination |
| **Collaboration** | **ESP** | **Membership, roles, patterns, lifecycle** |

A2A answers *how one agent delegates work to another*. SLIM answers *how messages move securely at scale*. ESP answers *how N niche agents collaborate as a bounded group*.

## Repository layout

```
SPEC.md           Protocol specification
BINDINGS.md       Transport binding profiles (A2A-relay, SLIM)
GOVERNANCE.md     Project governance and path to neutral stewardship
CONTRIBUTING.md   How to contribute
schemas/          JSON Schema definitions
docs/             Cross-protocol alignment proposals
examples/         Reference ensemble definitions
sdk/python/       Reference Python SDK
```

## Quick start (Python)

```bash
cd sdk/python
pip install -e ".[a2a]"
```

```python
from ensemble_protocol import Ensemble, Member, Role, CoordinationPattern
from ensemble_protocol.bindings.a2a_relay import A2ARelayBinding

ensemble = Ensemble.create(
    coordinator="financial-agent",
    namespace="bknight.dev",
    name="invoice-delivery-2026-06-25",
    members=[
        Member(agent_ref="document-agent", role=Role.SPECIALIST, skills=["document.ingest"]),
        Member(agent_ref="email-agent", role=Role.SPECIALIST, skills=["send_document"]),
    ],
)

binding = A2ARelayBinding(
    platform_url="http://localhost:8000",
    api_key="…",
    caller_agent_id="financial-agent",
)

# Broadcast intent to all specialists; binding fans out via A2A relay (shared contextId).
replies = binding.execute(ensemble, CoordinationPattern.BROADCAST, "Deliver invoice #1042")
```

## Status

**v0.1.0 — draft.** Spec and A2A-relay binding are reference implementations. SLIM binding is specified but not yet implemented.

## Relationship to other protocols

- **A2A**: ESP envelopes carry A2A `Message` payloads; A2A-relay binding maps `ensemble_id` → `contextId`.
- **SLIM / AGNTCY Collaboration Context**: Compatible lifecycle states; SLIM binding carries ESP envelopes as message bodies. See [docs/alignment-agntcy-collaboration-context.md](docs/alignment-agntcy-collaboration-context.md).
- **MCP**: Specialists invoke tools locally; ESP coordinates *which* specialist acts and *when*.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [GOVERNANCE.md](GOVERNANCE.md).

## License

Apache-2.0