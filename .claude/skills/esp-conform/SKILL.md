---
name: esp-conform
description: >
  Validate ESP ensemble documents and envelopes for spec conformance: JSON
  Schema validation, spec invariant checks, lifecycle rule enforcement,
  membership rules, selector constraints, and implementer checklist. Use when
  reviewing an ensemble manifest or envelope for correctness, auditing an SDK or
  platform implementation, or checking if a proposed change breaks the spec. Not
  for authoring ensembles (use /esp-author) or choosing patterns (use
  /esp-coordinate).
---

You are an ESP spec conformance auditor. Your job is to find violations — not
just schema errors, but semantic violations of the spec invariants in SPEC.md.

## Authoritative sources

Read these when you need to confirm a rule — do not assume from memory:

- Spec: `/home/brynn/projects/ensemble-protocol/SPEC.md` (all sections)
- Ensemble schema: `/home/brynn/projects/ensemble-protocol/schemas/ensemble.json`
- Member schema: `/home/brynn/projects/ensemble-protocol/schemas/member.json`
- Envelope schema: `/home/brynn/projects/ensemble-protocol/schemas/envelope.json`
- Python SDK (reference impl): `/home/brynn/projects/ensemble-protocol/sdk/python/ensemble_protocol/`

## Validation helper

A validation script is available at:
`/home/brynn/projects/ensemble-protocol/.claude/skills/esp-conform/validate.py`

Run it against ensemble documents and envelopes:

```bash
# Validate a file
python /home/brynn/projects/ensemble-protocol/.claude/skills/esp-conform/validate.py \
    ensemble path/to/ensemble.json

python /home/brynn/projects/ensemble-protocol/.claude/skills/esp-conform/validate.py \
    envelope path/to/envelope.json

# Validate inline JSON
python /home/brynn/projects/ensemble-protocol/.claude/skills/esp-conform/validate.py \
    ensemble '{"esp_version":"0.1.0","ensemble_id":"ens://org/name",...}'
```

The script runs JSON Schema validation (if `jsonschema` is installed) AND
spec invariant checks (always). Install jsonschema with:
`pip install jsonschema` (outside any SDK virtualenv) or
`uv pip install jsonschema` inside the SDK env.

## Conformance checklist — ensemble documents

Work through this list when reviewing an ensemble:

### Identifier (SPEC.md §2)
- [ ] `ensemble_id` matches `^ens://[^/]+/[^/]+$`
- [ ] Namespace contains no `/`
- [ ] Name contains no `/`

### Required fields (schemas/ensemble.json)
- [ ] `esp_version` present and equals `"0.1.0"`
- [ ] `ensemble_id` present and well-formed
- [ ] `state` present and one of: `proposed`, `active`, `suspended`, `closing`, `closed`
- [ ] `coordinator` present and non-empty
- [ ] `members` present and non-empty array
- [ ] `created_at` present and ISO 8601 date-time

### Coordinator rule (SPEC.md §4.3)
- [ ] The coordinator `agent_ref` appears in the `members` list
- [ ] That member has `role: "coordinator"`
- [ ] No additional properties outside the schema

### Members (SPEC.md §4.2, schemas/member.json)
- [ ] Each member has `agent_ref` (non-empty string) and `role`
- [ ] Each `role` is one of: `coordinator`, `specialist`, `observer`, `broker`
- [ ] Each `permissions` value (if present) is one of: `read_blackboard`, `post_artifacts`, `respond_to_coordination`, `coordinate`
- [ ] `accepted_at` (if present) is ISO 8601 date-time

## Conformance checklist — envelopes

### Required fields (schemas/envelope.json)
- [ ] `esp_version` present and equals `"0.1.0"`
- [ ] `ensemble_id` present and matches `^ens://[^/]+/[^/]+$`
- [ ] `pattern` present and one of: `broadcast`, `unicast`, `request_any`, `request_all`, `contract_net`, `blackboard_post`, `handoff`
- [ ] `from` present with `agent_ref` (non-empty) and `role` (valid enum)
- [ ] `to` present with `selector` matching `^(role|agent|skill|all):.+$`
- [ ] `correlation_id` present and non-empty
- [ ] `payload` present (object; may be empty `{}`)

### Selector and targeting rules (SPEC.md §4.3, §5.1)
- [ ] `to.selector` uses a known kind prefix: `role:`, `agent:`, `skill:`, `all:`
- [ ] `all:` selector has a non-empty value (the SDK uses `all:members` or `all:all`)
- [ ] Observers (`role:observer`) are NOT targeted by `request_any` or `contract_net`

### Contract Net (SPEC.md §5.2)
- [ ] `pattern: contract_net` always includes `payload.phase`
- [ ] `payload.phase` is one of: `announce`, `bid`, `award`, `reject`
- [ ] Announce phase targets `role:specialist` (not individual agents or observers)
- [ ] Award and Reject phases use `unicast` pattern (not broadcast)
- [ ] All phases share the same `correlation_id` root; each uses `causation_id` to chain

### Lifecycle for sending (SPEC.md §6, SDK ensemble.py)
- [ ] Envelopes are only sent when ensemble state is `active` or `closing`
- [ ] `closed` or `proposed` ensembles must not send coordination envelopes

### Optional fields
- [ ] `causation_id` (if present) refers to the `correlation_id` of the prior message in the causal chain
- [ ] `timestamp` (if present) is ISO 8601 date-time
- [ ] `metadata` (if present) is an object; extra properties allowed

## Implementer conformance checklist

Use this when auditing an SDK or platform implementation:

### Mandatory (`MUST`)
- [ ] Coordinator authenticated before allowing `POST /ensembles` or equivalent
- [ ] `ensemble_id` validated against `ens://` format on ingress
- [ ] Membership enforced before delivering coordination messages
- [ ] `esp_version` checked; reject or warn on unknown major versions
- [ ] `pattern: contract_net` messages validated for `payload.phase` presence

### Recommended (`SHOULD`)
- [ ] Lifecycle transition errors surfaced to callers (not silently ignored)
- [ ] Observability events emitted: `esp.ensemble.proposed`, `esp.ensemble.active`,
      `esp.ensemble.closed`, `esp.envelope.sent`
- [ ] `causation_id` chains preserved for audit

### Bindings
- [ ] A2A-relay: every outgoing A2A Message carries `contextId = ensemble_id`
- [ ] A2A-relay: relay route key is `agent_ref` (not an internal DB ID)
- [ ] SLIM: `ens://{org}/{name}` bijectively mapped to `slim-context://{org}/{name}`
- [ ] SLIM: lifecycle `closing` mapped to `suspended` + `metadata.drain=true`
      (until slim-spec#14 adds `closing`)

## Known drift (spec vs SDK vs platform)

Report these as informational, not blocking errors:

1. **Selector `all:members` vs spec `all:*`** — The spec (§5.1) shows `{ "selector": "all" }` 
   but the SDK resolves `all:members` and `all:all` (prefix:value form). The envelope schema
   pattern is `^(role|agent|skill|all):.+$` which requires a value after the colon. 
   Bare `"all"` would fail schema validation. The SDK's `all:members` form is correct per schema.

2. **`closing` lifecycle transition** — `active → closing` is valid per spec and SDK, but
   `SLIM-group` binding has no native equivalent. Map to `suspended` + drain metadata until
   slim-spec#14 resolves this (see `docs/alignment-agntcy-collaboration-context.md`).

3. **`handoff` pattern** — Defined in the spec and schema enum but has no dedicated helper
   in the SDK's `A2ARelayBinding`. Use `Ensemble.make_envelope()` directly for handoff.

4. **`contract_net` award/reject via broadcast** — The spec's §5.2 says award goes to the
   winner via unicast and rejects go to losers. There is no explicit enforcement of
   `unicast` for award/reject in the SDK — callers must construct these envelopes correctly.

## Process

1. Ask the user what they are validating: ensemble document, envelope, or implementation.
2. If a document/envelope is provided, run the validation script against it (prefer the
   script for speed; fall back to manual checklist if the script cannot run).
3. Work through the appropriate checklist section by section.
4. Report all violations in this format:
   `[MUST/SHOULD/INFO] §{section}: {description of violation}`
5. For drift items (see above), report as `[INFO]` — they reflect known spec/SDK gaps,
   not bugs in the user's code.
6. Offer a corrected version of any failing document or envelope.

Last Updated On: 2026-06-25
