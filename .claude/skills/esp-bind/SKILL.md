---
name: esp-bind
description: >
  Wire an ESP ensemble to a transport binding: A2A-relay (ensemble_id as
  contextId), SLIM-group, or direct-HTTP. Use when configuring how envelopes
  are physically delivered, understanding the ID mapping between ESP and a
  transport, integrating with a platform SDK (a2a-platform esp.py), or choosing
  between binding profiles. Not for authoring ensembles (use /esp-author) or
  choosing coordination patterns (use /esp-coordinate).
---

You are an expert in the Ensemble Protocol (ESP) transport bindings. Help the
user wire an ESP ensemble to the correct physical transport.

## Authoritative sources

Read these when you need to confirm a detail — do not assume from memory:

- Bindings spec: `/home/brynn/projects/ensemble-protocol/BINDINGS.md`
- A2A relay binding SDK: `/home/brynn/projects/ensemble-protocol/sdk/python/ensemble_protocol/bindings/a2a_relay.py`
- Platform ESP integration: `/home/brynn/projects/a2a-platform/sdk/python/a2a_platform/esp.py`
- Platform ensemble router: `/home/brynn/projects/a2a-platform/api/app/modules/ensembles/router.py`
- E2E test (working wiring example): `/home/brynn/projects/a2a-platform/tests/e2e_esp.py`
- SLIM alignment: `/home/brynn/projects/ensemble-protocol/docs/alignment-agntcy-collaboration-context.md`

## Binding profiles

| Profile | Status | Best for |
|---------|--------|----------|
| **a2a-relay** | Reference implementation (Python) | Federated SaaS agents behind a platform relay; billing, allowlists, audit |
| **slim-group** | Specified, not yet implemented | Cross-org E2E encryption, native multicast |
| **direct-http** | Specified, not yet implemented | Local dev, same VPC, no broker |

## A2A-relay binding (reference implementation)

### ID mapping

| ESP | A2A / relay |
|-----|-------------|
| `ensemble_id` | `contextId` on every A2A Message in this ensemble |
| `correlation_id` | `messageId` or `metadata.esp_correlation_id` |
| `workflow_id` (in envelope metadata) | `metadata.workflow_id` on A2A Message |
| Member `agent_ref` | Relay route key — `POST /a2a/{agent_ref}` |

The relay groups all pairwise tasks sharing a `contextId` into one thread.

### Pattern execution over A2A-relay

- **broadcast/request_all** — N sequential (or concurrent) pairwise A2A calls,
  each stamped with `contextId = ensemble_id`. Not native multicast.
- **unicast** — single A2A call; selector must resolve to exactly one agent.
- **request_any** — fan out concurrently; return first response; cancel pending
  tasks. Implemented with `asyncio.wait(return_when=FIRST_COMPLETED)`.
- **contract_net** — announce = broadcast to specialists; bid = unicast to
  coordinator; award/reject = unicast to winner/losers.
- **blackboard_post** — binding-specific: store artifact keyed by `ensemble_id`
  or embed in A2A Message parts and broadcast a notification.

### Authentication

- Caller authenticates to relay: `Authorization: Bearer {api_key}`
- Relay enforces owner allowlist before forwarding
- Target agent validates relay's credentials per Agent Card auth schemes

### Using the ESP reference binding (standalone)

```python
from ensemble_protocol.bindings.a2a_relay import A2ARelayBinding

binding = A2ARelayBinding(
    platform_url="http://localhost:8000",
    api_key="your-api-key",
    caller_agent_id="financial-agent",
    timeout=60.0,
)

# Execute a pattern and get replies {agent_ref: reply_text}
replies = binding.execute(
    ensemble, CoordinationPattern.BROADCAST, "Deliver invoice #1042"
)

# Or call pattern-specific helpers
replies = binding.broadcast(ensemble, "Notify all specialists")
reply   = binding.unicast(ensemble, "document-agent", "Ingest this PDF")
```

The binding requires `httpx` and optionally `a2a-sdk` (for streaming).
Install with: `pip install -e ".[a2a]"` in `sdk/python/`.

### Using the a2a-platform SDK integration

The a2a-platform provides `register_ensemble`, `get_ensemble`, and `coordinate`
in `a2a_platform/esp.py`. These layer on top of the platform Agent's existing
relay client rather than using the standalone binding.

```python
from a2a_platform import Agent
from ensemble_protocol import Ensemble, Member, Role, CoordinationPattern

# Create and register the ensemble (coordinator must match caller agent_id)
ensemble = Ensemble.create(
    coordinator="agent-a",
    namespace="my-platform.dev",
    name="my-collaboration",
    members=[
        Member(agent_ref="agent-b", role=Role.SPECIALIST),
        Member(agent_ref="agent-c", role=Role.SPECIALIST),
    ],
)
agent.register_ensemble(ensemble)   # POST /ensembles

# Coordinate via the platform relay (uses ensemble_id as contextId)
replies = agent.coordinate(
    ensemble, CoordinationPattern.BROADCAST, "hi from ESP"
)

# Retrieve stored ensemble + relay thread participants
stored = agent.get_ensemble(ensemble.ensemble_id)
# stored: {"ensemble_id": ..., "doc": {...}, "participants": [...]}
```

Install with: `pip install -e ".[esp]"` in the platform SDK.

The `register_ensemble` call enforces that `doc.coordinator == agent.agent_id`.
The platform registry stores the manifest and creates a Thread keyed by
`ensemble_id` (which becomes the A2A `contextId`).

## SLIM-group binding (specified, not yet implemented)

### ID mapping

| ESP | SLIM |
|-----|------|
| `ens://{org}/{name}` | `SlimContextHeader.context_id`; bijective alias of `slim-context://{org}/{name}` |
| Envelope body | SLIM message data payload (JSON-serialized ESP Envelope) |
| `SlimContextHeader.sequence` | Per-sender ordering for audit/gap detection |
| Group channel | SLIM Group created per ensemble on `active` transition |

### Lifecycle → SLIM actions

- `proposed` → create Collaboration Context (no traffic yet)
- `active` → create SLIM Group, add members via MLS
- `closed` → tear down group, emit `esp.ensemble.closed`

The `closing` state has no direct SLIM equivalent; map it to `suspended` with
`metadata.drain=true` until slim-spec#14 adds `closing` support.

See `docs/alignment-agntcy-collaboration-context.md` for the full mapping
proposal and open questions.

## Direct-HTTP binding (specified, not yet implemented)

For agents in the same trust zone without a relay:

```
POST /ensembles/{ensemble_id}/messages    # send envelope
GET  /ensembles/{ensemble_id}             # fetch ensemble doc
POST /ensembles                           # create
POST /ensembles/{id}/members              # add member
POST /ensembles/{id}/lifecycle            # transition state
```

## Choosing a binding

Ask the user these questions:

1. Do you have a platform relay (A2A, billing, allowlists)? → **a2a-relay**
2. Do you need cross-org E2E encryption and native multicast? → **slim-group** (once implemented)
3. Are all agents in the same VPC or local dev? → **direct-http** (once implemented)
4. Are you using the a2a-platform SDK? → use `agent.coordinate()` / `agent.register_ensemble()` rather than the standalone binding.

## Process

1. Identify which binding the user needs (ask if not clear).
2. Show the ID mapping table for that binding.
3. Provide a working code snippet for their exact setup — prefer the
   a2a-platform SDK path if they are on that platform, otherwise the
   standalone `A2ARelayBinding`.
4. Note authentication requirements: relay Bearer token, allowlist setup.
5. If the user is doing SLIM or direct-HTTP, clarify that those bindings are
   spec-only and not yet implemented in the Python SDK.
6. For validation, direct to `/esp-conform`.

Last Updated On: 2026-06-25
