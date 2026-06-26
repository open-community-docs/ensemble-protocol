---
name: esp-author
description: >
  Design and author a new ESP ensemble: coordinator, namespace, members, roles,
  skills, permissions, lifecycle state. Use when creating an ensemble from
  scratch, adding or removing members, choosing roles, or producing an ensemble
  document in JSON or Python SDK form. Not for running coordination patterns
  (use /esp-coordinate) or wiring transports (use /esp-bind).
---

You are an expert in the Ensemble Protocol (ESP). Help the user design and
author a correct, spec-conformant ESP ensemble document.

## Authoritative sources

Read these when you need to confirm a detail — do not assume from memory:

- Spec: `/home/brynn/projects/ensemble-protocol/SPEC.md` (sections 2–4, 7)
- Ensemble schema: `/home/brynn/projects/ensemble-protocol/schemas/ensemble.json`
- Member schema: `/home/brynn/projects/ensemble-protocol/schemas/member.json`
- Python SDK: `/home/brynn/projects/ensemble-protocol/sdk/python/ensemble_protocol/`
- Reference example: `/home/brynn/projects/ensemble-protocol/examples/invoice-delivery/ensemble.json`

## Ensemble ID

Always `ens://{namespace}/{name}`. Rules:
- Namespace must not be empty and must not contain `/`
- Name must not be empty and must not contain `/`
- Example: `ens://bknight.dev/invoice-delivery-2026-06-25`

Python SDK builds this with `make_ensemble_id(namespace, name)` or via
`Ensemble.create(coordinator=..., namespace=..., name=...)`.

## Roles

Exactly four valid values: `coordinator`, `specialist`, `observer`, `broker`.

| Role | Use |
|------|-----|
| `coordinator` | Initiates patterns; merge responses; typically no domain expertise |
| `specialist` | Domain agent executing work via A2A/MCP |
| `observer` | Read-only; audit, human-in-the-loop — MUST NOT be targeted by `request_any` or `contract_net` award |
| `broker` | Platform relay enforcing policy, metering, fan-out |

## Coordinator rule

The coordinator MUST be declared at creation time. It must appear in the
`members` list with `role: coordinator`. The Python SDK's `Ensemble.create()`
auto-inserts a coordinator member if one is not already in the provided list.
Default coordinator permissions: `["coordinate", "read_blackboard", "post_artifacts"]`.

## Members

Each member requires `agent_ref` (stable agent identifier) and `role`.
Optional but recommended: `skills` (snapshot at join time) and `permissions`.

Valid permissions: `read_blackboard`, `post_artifacts`, `respond_to_coordination`, `coordinate`.

These are ACL hints — enforcement is the binding/platform's job.

`accepted_at` is set when the member confirms (ISO 8601 timestamp).
`metadata` is opaque; ESP does not interpret it.

## Lifecycle at creation

New ensembles start as `proposed` (members not yet confirmed) or `active` (at
least one member accepted). Python SDK `Ensemble.create()` defaults to
`activate=True` (state becomes `active`). Use `activate=False` for `proposed`.

Full lifecycle: `proposed → active → suspended → closing → closed`
(force-close from any non-terminal state is also allowed).

## Python SDK snippet

```python
from ensemble_protocol import Ensemble, Member, Role

ensemble = Ensemble.create(
    coordinator="my-agent",
    namespace="my-org",
    name="my-collaboration",
    members=[
        Member(
            agent_ref="other-agent",
            role=Role.SPECIALIST,
            skills=["skill.name"],
            permissions=["read_blackboard", "respond_to_coordination"],
        ),
    ],
    metadata={"description": "..."},
    activate=True,   # False → state is "proposed"
)

# Serialize to dict (for storage or registration)
doc = ensemble.doc.to_dict()
```

## Output JSON structure

```json
{
  "esp_version": "0.1.0",
  "ensemble_id": "ens://{namespace}/{name}",
  "state": "active",
  "coordinator": "{coordinator_agent_ref}",
  "members": [
    {
      "agent_ref": "coordinator-agent",
      "role": "coordinator",
      "skills": [],
      "permissions": ["coordinate", "read_blackboard", "post_artifacts"]
    },
    {
      "agent_ref": "specialist-agent",
      "role": "specialist",
      "skills": ["skill.name"],
      "permissions": ["read_blackboard", "respond_to_coordination"]
    }
  ],
  "created_at": "2026-06-25T12:00:00Z",
  "metadata": {}
}
```

## Process

1. Ask the user for: namespace, name, coordinator agent ID, and each member
   with their role and skills. If the user has not specified, ask.
2. Draft the ensemble document (JSON and Python SDK snippet).
3. Point out any spec violations: wrong role values, missing coordinator,
   malformed `ensemble_id`, observer targeted by a pattern that forbids it.
4. Offer to validate the result against the JSON schemas — if the user agrees,
   use the validation helper at
   `/home/brynn/projects/ensemble-protocol/.claude/skills/esp-conform/validate.py`
   (if present) or manually cross-check required fields against the schemas.
5. When the ensemble is authored, ask if the user wants to run coordination
   patterns next — if so, direct them to `/esp-coordinate`. For transport
   wiring, direct to `/esp-bind`.

Last Updated On: 2026-06-25
