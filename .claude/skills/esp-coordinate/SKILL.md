---
name: esp-coordinate
description: >
  Choose and execute an ESP coordination pattern on an existing ensemble:
  broadcast, unicast, request_any, request_all, contract_net, blackboard_post,
  handoff. Use when you have an ensemble and want to send coordination messages,
  understand which pattern fits a use case, construct envelopes, or work through
  the contract_net three-phase flow. Not for authoring the ensemble itself (use
  /esp-author) or configuring transport bindings (use /esp-bind).
---

You are an expert in the Ensemble Protocol (ESP). Help the user choose and
execute the right coordination pattern for their use case.

## Authoritative sources

Read these when you need to confirm a detail — do not assume from memory:

- Spec: `/home/brynn/projects/ensemble-protocol/SPEC.md` (sections 5–6)
- Envelope schema: `/home/brynn/projects/ensemble-protocol/schemas/envelope.json`
- Python SDK ensemble.py: `/home/brynn/projects/ensemble-protocol/sdk/python/ensemble_protocol/ensemble.py`
- Python SDK patterns.py: `/home/brynn/projects/ensemble-protocol/sdk/python/ensemble_protocol/patterns.py`
- Reference demo: `/home/brynn/projects/ensemble-protocol/examples/invoice-delivery/demo.py`

## Pattern reference

| Pattern | Routing | When to use |
|---------|---------|-------------|
| `broadcast` | 1 → all targeted members | Same payload to every recipient; all may respond |
| `unicast` | 1 → exactly 1 | Direct message within ensemble; requires `agent:{id}` or `skill:{name}` that resolves to one member |
| `request_any` | 1 → group, first wins | First acceptable response wins; rest may be cancelled — use for latency-sensitive tasks where any specialist will do |
| `request_all` | 1 → group, collect all | Wait for every response then merge — use when you need all perspectives or votes |
| `contract_net` | 3-phase announce/bid/award | FIPA-style negotiation: announce task → collect bids → award to winner |
| `blackboard_post` | 1 → blackboard | Publish artifact; subscribers react asynchronously |
| `handoff` | 1 → 1 | Transfer coordinator role or task ownership to another member |

## Addressing selectors

Selectors resolve against the ensemble membership at routing time:

```
{ "selector": "role:specialist" }    # all members with that role
{ "selector": "agent:email-agent" }  # one specific agent_ref
{ "selector": "skill:document.ingest" }  # members whose skills list contains this
{ "selector": "all:members" }        # every member
```

Python SDK factory methods: `Addressing.role(Role.SPECIALIST)`,
`Addressing.agent("email-agent")`, `Addressing.skill("document.ingest")`,
`Addressing.all_members()`.

Observers MUST NOT be targeted by `request_any` or `contract_net` award.

## Contract Net (three-phase) walkthrough

All three phases share the same `correlation_id` root; each phase has its own
`causation_id` pointing at the previous message.

1. **Announce** (coordinator → `role:specialist`): `pattern: contract_net`,
   `payload.phase: "announce"`, payload describes the task.
2. **Bid** (specialists → coordinator via unicast): `pattern: contract_net`,
   `payload.phase: "bid"`, payload contains capability/cost/ETA.
3. **Award** (coordinator → winning agent): `pattern: contract_net`,
   `payload.phase: "award"`.
   **Reject** (coordinator → all other bidders): `payload.phase: "reject"`.

## Envelope required fields

```json
{
  "esp_version": "0.1.0",
  "ensemble_id": "ens://{namespace}/{name}",
  "pattern": "broadcast",
  "from": { "agent_ref": "coordinator-agent", "role": "coordinator" },
  "to": { "selector": "role:specialist" },
  "correlation_id": "msg-unique-id",
  "payload": { "intent": "deliver_invoice", "text": "..." }
}
```

Optional envelope fields: `causation_id`, `timestamp`, `metadata`
(carry `workflow_id`, `idempotency_key`, etc.).

For `contract_net`, `payload.phase` is required.

## Python SDK usage

```python
from ensemble_protocol import Ensemble, CoordinationPattern
from ensemble_protocol.models import Addressing, Payload

# Method 1 — Ensemble.make_envelope() (low-level, any pattern)
envelope = ensemble.make_envelope(
    CoordinationPattern.UNICAST,
    to=Addressing.agent("document-agent"),
    payload=Payload(
        intent="ingest_invoice_pdf",
        text="Ingest invoice inv-1042.pdf",
    ),
    causation_id=previous_correlation_id,
    metadata={"idempotency_key": "inv-1042-ingest"},
)
wire_dict = envelope.to_dict()  # serialize for transport

# Method 2 — make_envelope() convenience helper
from ensemble_protocol import make_envelope
env = make_envelope(
    ensemble,
    CoordinationPattern.BROADCAST,
    text="Deliver invoice #1042",
    intent="deliver_invoice",
    to_selector="role:specialist",
)

# Method 3 — A2ARelayBinding.execute() (runs the pattern, returns replies)
from ensemble_protocol.bindings.a2a_relay import A2ARelayBinding
binding = A2ARelayBinding(
    platform_url="http://localhost:8000",
    api_key="...",
    caller_agent_id="financial-agent",
)
replies = binding.execute(
    ensemble, CoordinationPattern.BROADCAST, "Deliver invoice #1042"
)
# replies: {"agent-b": "...", "agent-c": "..."}
```

`make_envelope()` raises `RuntimeError` if the ensemble is not in `active` or
`closing` state. `resolve()` raises `ValueError` for an unknown selector kind
or a selector with no targets.

## Coordination pattern decision guide

Ask the user these questions to narrow the choice:

1. Do you need a response from **one** specific agent? → `unicast`
2. Do you need responses from **all** specialists? → `request_all`
3. Do you need the **fastest** response and any specialist will do? → `request_any`
4. Do you want to **negotiate** which specialist gets the task? → `contract_net`
5. Do you want to **notify all** specialists (each may respond)? → `broadcast`
6. Are you **posting an artifact** for asynchronous pickup? → `blackboard_post`
7. Are you **transferring ownership** of the task or coordinator role? → `handoff`

## Process

1. Understand the user's coordination goal (what they want to happen and who
   should receive the message).
2. Recommend the pattern that best fits, explaining the trade-off.
3. Show the envelope JSON and/or Python SDK snippet for that pattern.
4. For `contract_net`, walk through all three phases explicitly.
5. Note any spec constraints: observer targeting restrictions, unicast requiring
   exactly one resolved target, `contract_net` requiring `payload.phase`.
6. If the user needs to execute the pattern over a real transport, direct
   them to `/esp-bind`.

Last Updated On: 2026-06-25
