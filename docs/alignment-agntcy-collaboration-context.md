# Alignment Proposal: ESP ↔ AGNTCY Collaboration Context

**Status:** Draft for community review  
**Version:** 0.1.0  
**Date:** 2026-06-25  
**Authors:** Ensemble Protocol maintainers  
**Related work:** [slim-spec#14 — Collaboration Context Extension](https://github.com/agntcy/slim-spec/issues/14)

## Summary

[Ensemble Protocol (ESP)](../SPEC.md) and the proposed [AGNTCY Collaboration Context](https://github.com/agntcy/slim-spec/issues/14) extension solve adjacent problems in the multi-agent stack:

| Layer | AGNTCY Collaboration Context | Ensemble Protocol (ESP) |
|-------|------------------------------|-------------------------|
| Scope | SLIM transport headers + lifecycle + membership manifest | Transport-agnostic coordination semantics |
| Primary job | Bound cross-org interactions on the wire | Define *how* agents collaborate inside that bound |
| Transport | SLIM-native | SLIM-group, A2A-relay, direct HTTP |

**Proposal:** Treat Collaboration Context as the **SLIM binding's scope and lifecycle plane**. Treat ESP as the **semantic layer** carried inside Collaboration Context messages. Converge identifiers and lifecycle; keep ESP patterns and roles as the value-add above SLIM.

This is complementary, not competitive.

## Problem statement

SLIM provides secure many-to-many transport. A2A provides pairwise task delegation. Neither defines, in a portable way:

- Which agents belong to a multi-party engagement
- What role each agent plays
- How a coordinator fans out work (`broadcast`, `request_any`, `contract_net`, …)
- How messages correlate across a group workflow

[slim-spec#14](https://github.com/agntcy/slim-spec/issues/14) addresses the **first and last mile on SLIM**: context identity, lifecycle, membership manifest, optional message headers, opaque governance metadata, and observability hooks.

ESP addresses **coordination semantics** that apply whether the binding is SLIM, an HTTP relay, or direct HTTP — the layer AGNTCY's RFC explicitly leaves to platforms.

Together they complete the stack:

```
┌─────────────────────────────────────────────┐
│  A2A / MCP — task & tool execution          │
├─────────────────────────────────────────────┤
│  ESP — patterns, roles, envelopes           │  ← semantic
├─────────────────────────────────────────────┤
│  Collaboration Context — scope & lifecycle    │  ← SLIM scope
├─────────────────────────────────────────────┤
│  SLIM Groups — secure multicast transport     │  ← wire
└─────────────────────────────────────────────┘
```

## Concept mapping

### Identifiers

| Collaboration Context (RFC) | ESP | Proposed convergence |
|-----------------------------|-----|----------------------|
| `slim-context://{initiator-org}/{context-id}` | `ens://{namespace}/{name}` | **Bijective mapping** — see below |

**Proposed rule:** When ESP uses the SLIM-group binding, `ensemble_id` MUST map to Collaboration Context ID as:

```
ens://{org}/{name}  ↔  slim-context://{org}/{name}
```

The URI scheme differs by binding profile; the `{org}/{name}` tuple is identical. Non-SLIM bindings (A2A-relay) use `ens://` only and map `ensemble_id` → A2A `contextId`.

### Lifecycle

| Collaboration Context | ESP | Notes |
|-----------------------|-----|-------|
| `proposed` | `proposed` | Identical |
| `active` | `active` | Identical |
| `suspended` | `suspended` | Identical |
| `closed` | `closed` | Identical |
| — | `closing` | ESP-only drain state; maps to CC `suspended` or pre-`closed` on SLIM |

**Proposal for slim-spec#14:** Add optional `closing` state, OR document that `closing` is represented as `suspended` with `metadata.drain=true`. ESP will accept either in the SLIM binding.

### Membership

| Collaboration Context `ContextMembership` | ESP `Member` | Mapping |
|-------------------------------------------|--------------|---------|
| `context_id` | `ensemble_id` (in parent doc) | Same scoped ID |
| `organization` | — | ESP is agent-centric; org captured in `metadata` or Agent Card |
| `agents[]` | `agent_ref` per member | 1:1 |
| `accepted_at` | `accepted_at` | 1:1 |
| `metadata` (opaque) | `metadata` (opaque) | Platform governance; ESP does not interpret |

**Proposal:** SLIM membership manifest lists agents; ESP member records add **role**, **skills snapshot**, and **permissions hints** as extensions in ESP `Member.metadata` or a namespaced JSON field:

```json
{
  "esp_version": "0.1.0",
  "role": "specialist",
  "skills": ["document.ingest"],
  "permissions": ["respond_to_coordination"]
}
```

Collaboration Context parsers that do not understand ESP ignore this block.

### Message headers

| Collaboration Context `SlimContextHeader` | ESP `Envelope` | Mapping |
|-------------------------------------------|----------------|---------|
| `context_id` | `ensemble_id` | Same scope |
| `sequence` | — | **ESP should adopt** per-sender monotonic sequence in SLIM binding |
| `metadata` (opaque) | `metadata` (opaque) | Platform policy |
| — | `pattern` | ESP-specific; carried in payload |
| — | `correlation_id` / `causation_id` | ESP-specific; carried in payload |

**Proposal:** On SLIM, the message **data payload** is a serialized ESP `Envelope` JSON object. `SlimContextHeader` carries scope + sequence; ESP carries coordination semantics.

Example SLIM message body:

```json
{
  "esp_version": "0.1.0",
  "ensemble_id": "slim-context://bknight.dev/invoice-delivery-2026-06-25",
  "pattern": "unicast",
  "from": { "agent_ref": "financial-agent", "role": "coordinator" },
  "to": { "selector": "agent:document-agent" },
  "correlation_id": "msg-ingest-001",
  "payload": { "intent": "ingest_invoice_pdf", "text": "..." }
}
```

### SLIM Groups

Per slim-spec#14:

> A Collaboration Context MAY use SLIM Groups for its multicast.

ESP alignment:

| ESP pattern | SLIM Group usage |
|-------------|------------------|
| `broadcast` | Publish envelope to group channel |
| `request_any` / `request_all` | Group publish + reply correlation via `correlation_id` |
| `unicast` | Direct agent delivery (may bypass group fan-out) |
| `contract_net` | Multi-phase; same group, phase in `payload.phase` |
| `blackboard_post` | Group notification; artifact in payload or platform store |

**Groups provide transport; Collaboration Context provides scope; ESP provides coordination.**

## What ESP adds beyond slim-spec#14

The RFC deliberately excludes permission models, approval flows, and task semantics. ESP adds portable coordination primitives without prescribing enterprise policy:

1. **Roles** — `coordinator`, `specialist`, `observer`, `broker`
2. **Addressing selectors** — `role:specialist`, `skill:document.ingest`, `agent:email-agent`
3. **Coordination patterns** — `broadcast`, `unicast`, `request_any`, `request_all`, `contract_net`, `blackboard_post`, `handoff`
4. **Causality chain** — `correlation_id` + `causation_id` for multi-step workflows
5. **A2A payload slot** — `payload.a2a_message` for delegation through pairwise A2A under a group scope

## What ESP adopts from slim-spec#14

ESP maintainers propose adopting in the SLIM-group binding (v0.2):

1. **`sequence` field** — per-context, per-sender monotonic counter for gap detection and audit
2. **OTEL event names** — emit compatible events:
   - `slim.context.*` from Collaboration Context lifecycle
   - `esp.envelope.sent` with `pattern`, `ensemble_id`, `correlation_id`
3. **Opaque metadata slots** — no ESP interpretation of platform governance bytes
4. **Context URI scheme** — `slim-context://` as the SLIM-native alias of `ens://`

## A2A-relay binding (non-SLIM profile)

ESP's [A2A-relay binding](../BINDINGS.md) does not require Collaboration Context headers. Mapping:

| ESP | A2A relay |
|-----|-----------|
| `ensemble_id` | `contextId` on all Messages in the ensemble |
| Member `agent_ref` | Relay route key |

This profile is how federated agents collaborate today when SLIM is not deployed. Collaboration Context remains the preferred SLIM profile; A2A-relay is the **degraded but interoperable** profile.

## Recommended changes to slim-spec#14

We suggest the AGNTCY community consider:

1. **Reference profile for semantic payloads** — document that application protocols (A2A, ESP, custom) ride in the data payload; Collaboration Context does not mandate a single payload format.
2. **Optional `closing` lifecycle state** — or a documented `suspended` + drain metadata convention.
3. **Namespaced member extensions** — allow `metadata` to carry spec-specific member attributes (ESP, OASF) without SLIM interpreting them.
4. **Cross-reference** — link to ESP as an example semantic layer for group coordination patterns.

## Recommended changes to ESP

ESP maintainers commit to:

1. Implement `sdk/python/ensemble_protocol/bindings/slim_group.py` once slim-spec#14 stabilizes
2. Add `sequence` to envelopes in SLIM binding only (optional field in envelope `metadata.slim_sequence`)
3. Document bijective `ens://` ↔ `slim-context://` mapping in `BINDINGS.md` §2
4. Participate in slim-spec#14 discussion with this document as the reference alignment

## Interoperability test plan

| Test | Profiles involved | Pass criteria |
|------|-------------------|---------------|
| Lifecycle sync | SLIM CC + ESP | `proposed` → `active` → `closed` transitions observable via both APIs |
| Membership join | SLIM CC + ESP | Agent appears in both membership manifest and ESP ensemble doc |
| Broadcast | SLIM Group + ESP | One ESP `broadcast` envelope reaches all group members |
| A2A under scope | CC + ESP + A2A-relay | `payload.a2a_message` executes on specialist; `contextId` = `ensemble_id` |
| Sequence gap | SLIM header + ESP | Receiver detects missing `sequence` and surfaces audit event |

Reference scenario: [invoice-delivery ensemble](../examples/invoice-delivery/ensemble.json).

## Governance and standardization path

This alignment does not require immediate LF or AAIF donation. Suggested sequence:

1. **Now** — publish this proposal; comment on [slim-spec#14](https://github.com/agntcy/slim-spec/issues/14)
2. **Next** — prototype SLIM binding against AGNTCY slim Python bindings
3. **Then** — second independent implementer (relay broker or agent framework)
4. **Later** — AAIF Growth-stage proposal or AGNTCY sub-project, with aligned specs

## Open questions

1. Should `ens://` and `slim-context://` be formally registered as parallel schemes, or should ESP standardize on `slim-context://` whenever SLIM is present?
2. Should Collaboration Context own role/permission semantics eventually, or remain permanently in semantic layers like ESP?
3. How should `contract_net` phases interact with SLIM `sequence` ordering under concurrent bids?

## References

- [ESP Specification v0.1.0](../SPEC.md)
- [ESP Bindings](../BINDINGS.md)
- [AGNTCY Collaboration Context RFC (slim-spec#14)](https://github.com/agntcy/slim-spec/issues/14)
- [AGNTCY SLIM Overview](https://slim.agntcy.org/latest/slim/slim-overview/)
- [A2A Key Concepts — contextId](https://a2a-protocol.org/latest/topics/key-concepts/)
- [Linux Foundation AGNTCY Press Release](https://www.linuxfoundation.org/press/linux-foundation-welcomes-the-agntcy-project-to-standardize-open-multi-agent-system-infrastructure-and-break-down-ai-agent-silos)