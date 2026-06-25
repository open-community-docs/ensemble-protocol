# ESP Transport Bindings

ESP envelopes are transport-agnostic. This document defines how bindings map ESP semantics onto concrete transports.

## Binding profiles

| Profile | Status | Use when |
|---------|--------|----------|
| **a2a-relay** | Reference impl (Python) | Federated agents behind a platform relay; billing, allowlists, audit |
| **slim-group** | Spec only | Cross-org, low-latency, E2E encrypted multicast |
| **direct-http** | Spec only | Same-trust-zone agents without a broker |

## 1. A2A-relay binding

Maps ESP to [A2A](https://a2a-protocol.org) JSON-RPC over an HTTP relay that forwards pairwise agent traffic and groups messages by `contextId`.

### 1.1 ID mapping

| ESP | A2A / relay |
|-----|-------------|
| `ensemble_id` | `contextId` on every A2A Message in the ensemble |
| `correlation_id` | `messageId` or `metadata.esp_correlation_id` |
| `workflow_id` | `metadata.workflow_id` on A2A Message |
| Member `agent_ref` | Relay route key (`/a2a/{agent_ref}`) |

The relay groups all pairwise tasks sharing a `contextId` into one thread and records participants.

### 1.2 Pattern execution

#### `broadcast`

1. Coordinator binding resolves `to.selector` → list of member `agent_ref`s
2. For each target: `POST /a2a/{target}` with `message/send` or `message/stream`
3. Stamp `contextId = ensemble_id` on every outgoing Message
4. Collect replies; return `{agent_ref: reply_text}`

This is N pairwise A2A calls — no native multicast. Functionally equivalent to ESP broadcast for request/response workloads.

#### `unicast`

Single A2A call to `to.selector = agent:{id}` with shared `contextId`.

#### `request_any`

Fan out like `broadcast`; return first successful response; optionally cancel remaining (binding-specific).

#### `request_all`

Fan out like `broadcast`; wait for all responses (or timeout); return aggregated map.

#### `contract_net`

- `phase: announce` → `broadcast` to specialists
- `phase: bid` → specialists reply via `unicast` to coordinator
- `phase: award` → `unicast` to winner

#### `blackboard_post`

Binding-specific. Options:

- Store artifact in relay/platform store keyed by `ensemble_id`
- Or embed artifact in A2A Message `parts` and `broadcast` notification

### 1.3 Authentication

- Caller authenticates to relay: `Authorization: Bearer {api_key}`
- Relay enforces owner allowlist before forwarding
- Target agent validates relay's credentials per Agent Card `auth` schemes

### 1.4 Reference implementation

`sdk/python/ensemble_protocol/bindings/a2a_relay.py`

Any relay implementing `POST /a2a/{target_agent_id}` with shared `contextId` threading is compatible.

## 2. SLIM-group binding (specified, not implemented)

Maps ESP to [SLIM](https://slim.agntcy.org) group channels with optional [Collaboration Context](https://github.com/agntcy/slim-spec/issues/14) headers.

### 2.1 ID mapping

| ESP | SLIM |
|-----|------|
| `ensemble_id` | `SlimContextHeader.context_id` as `slim-context://{namespace}/{name}` |
| Envelope body | SLIM message data payload (JSON) |
| Group channel | SLIM Group created per ensemble on `active` transition |

### 2.2 Pattern execution

| Pattern | SLIM behavior |
|---------|---------------|
| `broadcast` | Publish to group channel; all members receive |
| `unicast` | Direct message to member's client locator |
| `request_any` / `request_all` | Group publish + reply-to channel (correlation ID) |
| `blackboard_post` | Publish artifact reference on group channel |

### 2.3 Lifecycle

- `proposed` → create Collaboration Context (no traffic)
- `active` → create SLIM Group, add members via MLS
- `closed` → tear down group, emit `esp.ensemble.closed`

## 3. Direct-HTTP binding (specified, not implemented)

For agents in the same trust zone without a relay.

```
POST /ensembles/{ensemble_id}/messages
Content-Type: application/json
Authorization: Bearer …

{ ESP envelope }
```

Ensemble state:

```
GET  /ensembles/{ensemble_id}
POST /ensembles                    # create
POST /ensembles/{id}/members       # add member
POST /ensembles/{id}/lifecycle     # transition state
```

## 4. Choosing a binding

| Requirement | Binding |
|-------------|---------|
| Federated SaaS, metering, allowlists | a2a-relay |
| Cross-org E2E encryption, native multicast | slim-group |
| Local dev, same VPC | direct-http |

Bindings MAY be combined: coordinator uses a2a-relay; a SLIM-connected peer bridges into a group channel for sub-ensemble sync.