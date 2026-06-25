# Contributing to Ensemble Protocol (ESP)

Thank you for helping build open collaboration semantics for multi-agent systems.

## What to contribute

| Area | Location | Notes |
|------|----------|-------|
| Protocol spec | `SPEC.md` | Normative behavior; discuss breaking changes in an issue first |
| JSON schemas | `schemas/` | Must match `SPEC.md` |
| Transport bindings | `BINDINGS.md`, `sdk/*/bindings/` | Describe mapping, not new coordination semantics |
| Reference SDK | `sdk/python/` | Must conform to spec; tests required |
| Examples | `examples/` | Realistic ensemble manifests and sequences |
| Alignment docs | `docs/` | Cross-protocol proposals and interoperability notes |

## Getting started

1. Open an issue describing the problem or use case (skip for typos and obvious fixes).
2. Fork or branch from `master`.
3. Make focused changes — one concern per pull request.
4. Run tests if you touched the SDK:

```bash
cd sdk/python
uv venv && uv pip install -e ".[dev]"
uv run pytest
```

5. Open a pull request with:
   - What changed and why
   - Whether `esp_version` needs a bump
   - How you validated the change (tests, example run, manual check)

## Contributor license agreement

By submitting a contribution, you agree that:

- Your contribution is your original work or you have rights to submit it
- Your contribution is licensed under [Apache-2.0](LICENSE)
- You grant the project maintainers the right to include it under that license

No separate CLA is required at this stage. If the project moves to Linux Foundation hosting, contributors may be asked to accept the LF contribution agreement for already-merged work at transfer time.

## Specification guidelines

When changing normative behavior:

- Prefer **optional** new fields and patterns (minor version) over breaking changes
- Update `schemas/` in the same PR as `SPEC.md`
- Add or update an example under `examples/` when introducing a new pattern
- Document binding impact in `BINDINGS.md` if transport mapping changes

### Naming and identifiers

- Ensemble IDs: `ens://{namespace}/{name}` — namespace must not contain `/`
- Pattern names: lowercase snake_case (`request_any`, `contract_net`)
- Role names: fixed enum in spec (`coordinator`, `specialist`, `observer`, `broker`)

## SDK guidelines

- Keep the Python SDK as a **reference implementation**, not the source of truth
- Public API changes should mirror spec concepts (`Ensemble`, `Envelope`, `CoordinationPattern`)
- Bindings must not embed platform-specific product names; describe the relay contract instead
- Add tests for member resolution, lifecycle transitions, and binding behavior

## Review expectations

Maintainers aim to respond within 5 business days. Normative PRs may need additional time for implementer feedback.

Labels:

- `spec` — normative protocol change
- `binding` — transport mapping
- `sdk` — reference implementation
- `breaking` — requires major `esp_version` bump

## Community channels

- **Issues and PRs** — primary discussion (this repository)
- **AGNTCY alignment** — see `docs/alignment-agntcy-collaboration-context.md`; feedback may also be posted to [slim-spec#14](https://github.com/agntcy/slim-spec/issues/14)

## Security

Report security issues privately to the maintainers via repository security advisories or direct contact through the account listed in `GOVERNANCE.md`. Do not open public issues for undisclosed vulnerabilities.