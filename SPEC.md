# Ensemble Protocol (ESP) — Specification v0.1.0

## 1. Overview

The Ensemble Protocol (ESP) defines interoperable **group collaboration semantics** for multi-agent systems where specialized agents run on independent infrastructure and organizational boundaries.

ESP is transport-agnostic and complements:

- **A2A** — pairwise task delegation and execution
- **MCP** — tool and resource access
- **SLIM** — secure many-to-many messaging transport

### 1.1 Design principles

1. **Complement, don't compete** — reuse Agent Cards, A2A Messages, SLIM groups.
2. **Thin pipe, rich platform** — ESP defines coordination primitives; platforms carry opaque governance metadata.
3. **Federated by default** — agents live on owner infrastructure; ensembles span trust boundaries.
4. **Explicit membership** — no emergent broadcast; every participant is declared.
5. **Bounded lifecycle** — every ensemble has a start and an end.

### 1.2 Terminology

| Term | Definition |
|------|------------|
| **Ensemble** | A bounded collaboration unit with identity, lifecycle, and membership |
| **Member** | An agent participating in an ensemble with a declared role |
| **Coordinator** | The member (or external broker) that initiates coordination patterns |
| **Envelope** | A transport-agnostic ESP message |
| **Pattern** | A coordination primitive (broadcast, contract_net, etc.) |
| **Blackboard** | Optional shared artifact store referenced by ensemble ID |
| **Binding** | Mapping from ESP envelopes to a transport (A2A-relay, SLIM, direct HTTP) |

## 2. Identifiers

### 2.1 Ensemble ID

```
ens://{namespace}/{name}
```

- `namespace` — organization or owner scope (e.g. `bknight.dev`, `acme-corp`)
- `name` — opaque, human-chosen identifier (e.g. `invoice-delivery-2026-06-25`)

Examples:

- `ens://bknight.dev/invoice-delivery-2026-06-25`
- `ens://acme-corp/deal-review-2026-q1`

### 2.2 Correlation

Every envelope MUST include:

- `correlation_id` — unique ID for this message
- `causation_id` (optional) — ID of the message that caused this one

Platforms MAY additionally carry `workflow_id` in `metadata` for cross-protocol audit (A2A `contextId`, MCP session, OTEL trace).

## 3. Lifecycle

```
proposed → active → suspended → closed
              ↓         ↓
           closing ─────┘
```

| State | Description |
|-------|-------------|
| `proposed` | Coordinator created ensemble; members not yet confirmed |
| `active` | At least one member accepted; coordination messages flow |
| `suspended` | Temporarily paused; new coordination rejected or queued |
| `closing` | Draining in-flight work; no new coordination |
| `closed` | Terminal; ensemble is immutable |

Transitions:

- `proposed` → `active` — coordinator or first member accepts
- `active` → `suspended` — coordinator suspends
- `suspended` → `active` — coordinator resumes
- `active` → `closing` — coordinator initiates shutdown
- `closing` → `closed` — all in-flight work complete or timeout
- `*` → `closed` — coordinator may force-close from any non-terminal state

Compatible with [AGNTCY Collaboration Context RFC](https://github.com/agntcy/slim-spec/issues/14) lifecycle (`proposed`, `active`, `suspended`, `closed`).

## 4. Members and roles

### 4.1 Roles

| Role | Description |
|------|-------------|
| `coordinator` | Initiates patterns; may merge responses; typically holds no domain expertise |
| `specialist` | Domain agent executing work via A2A/MCP |
| `observer` | Read-only participant (audit, human-in-the-loop) |
| `broker` | Platform relay enforcing policy, metering, fan-out |

### 4.2 Member record

```json
{
  "agent_ref": "document-agent",
  "role": "specialist",
  "skills": ["document.ingest"],
  "permissions": ["read_blackboard", "post_artifacts", "respond_to_coordination"],
  "accepted_at": "2026-06-25T12:00:00Z",
  "metadata": {}
}
```

- `agent_ref` — stable agent identifier (Agent Card ID, DID, or platform agent ID)
- `skills` — capability snapshot at join time (for routing; may drift — re-validate via Agent Card)
- `permissions` — ensemble-scoped ACL hints; enforcement is binding/platform responsibility
- `metadata` — opaque bytes/object; ESP does not interpret

### 4.3 Membership rules

- Each org/platform controls which of its agents join (per-org membership manifest)
- Coordinator MUST be declared at ensemble creation
- Members MAY leave unilaterally; coordinator MAY remove members in `proposed` or `active`
- Observers MUST NOT be targeted by `request_any` or `contract_net` award

## 5. Coordination patterns

Patterns are declared on each envelope. Execution maps to transport-specific fan-out (see BINDINGS.md).

| Pattern | Routing | Semantics |
|---------|---------|-----------|
| `broadcast` | 1 → all targeted members | Same payload to every recipient; all may respond |
| `unicast` | 1 → 1 | Direct message within ensemble |
| `request_any` | 1 → group | First acceptable response wins; others may be cancelled |
| `request_all` | 1 → group | Collect all responses; coordinator merges |
| `contract_net` | 1 → group | Announce task → collect bids → coordinator awards |
| `blackboard_post` | 1 → blackboard | Publish artifact; subscribers react asynchronously |
| `handoff` | 1 → 1 | Transfer coordinator role or task ownership |

### 5.1 Addressing (`to` selector)

```json
{ "selector": "role:specialist" }
{ "selector": "agent:email-agent" }
{ "selector": "skill:document.ingest" }
{ "selector": "all" }
```

Bindings resolve selectors against the ensemble membership manifest.

### 5.2 Contract Net (informative)

Inspired by FIPA Contract Net. Three-phase flow within one ensemble:

1. **Announce** — coordinator sends `contract_net` with `phase: announce` and task spec
2. **Bid** — specialists respond with `phase: bid` (capability, cost estimate, ETA)
3. **Award** — coordinator sends `phase: award` to winning agent; others get `phase: reject`

All phases use the same `correlation_id` root with phase-specific `causation_id` chains.

## 6. Envelope format

```json
{
  "esp_version": "0.1.0",
  "ensemble_id": "ens://bknight.dev/invoice-delivery-2026-06-25",
  "pattern": "broadcast",
  "from": {
    "agent_ref": "financial-agent",
    "role": "coordinator"
  },
  "to": {
    "selector": "role:specialist"
  },
  "correlation_id": "msg-8f3a2b1c",
  "causation_id": "msg-7b2c9d0e",
  "timestamp": "2026-06-25T12:00:00Z",
  "payload": {
    "intent": "deliver_invoice",
    "a2a_message": {
      "role": "user",
      "parts": [{ "text": "Ingest and deliver invoice #1042" }]
    }
  },
  "metadata": {
    "workflow_id": "wf-abc123",
    "idempotency_key": "inv-1042"
  }
}
```

### 6.1 Required fields

| Field | Type | Description |
|-------|------|-------------|
| `esp_version` | string | Protocol version (`0.1.0`) |
| `ensemble_id` | string | `ens://` URI |
| `pattern` | string | Coordination pattern name |
| `from` | object | Sender agent_ref + role |
| `to` | object | Recipient selector |
| `correlation_id` | string | Unique message ID |
| `payload` | object | Pattern-specific content |

### 6.2 Payload conventions

- `intent` (optional) — high-level goal string for logging/routing
- `a2a_message` (optional) — A2A Message object for bindings that delegate via A2A
- `artifact` (optional) — blackboard artifact reference or inline content
- `phase` (required for `contract_net`) — `announce` | `bid` | `award` | `reject`

## 7. Ensemble document

Full ensemble state (persisted by coordinator or broker):

```json
{
  "esp_version": "0.1.0",
  "ensemble_id": "ens://bknight.dev/invoice-delivery-2026-06-25",
  "state": "active",
  "coordinator": "financial-agent",
  "members": [ "..." ],
  "created_at": "2026-06-25T12:00:00Z",
  "metadata": {}
}
```

See `schemas/ensemble.json`.

## 8. Security (informative)

ESP does not define a new cryptographic layer. Bindings MUST:

- Authenticate senders via Agent Card auth, platform API keys, or SLIM/SPIFFE identity
- Enforce ensemble membership before delivering coordination messages
- Propagate `on_behalf_of` and `workflow_id` for audit chains
- Treat `metadata` as opaque; platforms embed governance policy references there

## 9. Observability (informative)

Implementations SHOULD emit events on lifecycle transitions:

- `esp.ensemble.proposed`
- `esp.ensemble.active`
- `esp.ensemble.suspended`
- `esp.ensemble.closed`
- `esp.ensemble.member.joined`
- `esp.ensemble.member.left`
- `esp.envelope.sent` (with `pattern`, `ensemble_id`, `correlation_id`)

Compatible with AGNTCY observability and OpenTelemetry.

## 10. Versioning

- `esp_version` follows semver
- Minor versions add optional fields and patterns; patch versions clarify spec text
- Major versions may break envelope schema