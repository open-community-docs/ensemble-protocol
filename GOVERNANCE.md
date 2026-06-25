# Governance

The Ensemble Protocol (ESP) is an open, vendor-neutral specification for group
collaboration among specialized AI agents. This document describes how the
project is led, how decisions are made, and how we intend to evolve toward
foundation-ready governance.

## Principles

1. **Complement existing standards** — ESP must not fork or replace A2A, MCP, or SLIM.
2. **Spec before implementation** — normative behavior lives in `SPEC.md` and `schemas/`; SDKs are reference implementations.
3. **Transport agnostic** — coordination semantics are independent of relay, SLIM, or direct HTTP bindings.
4. **Thin protocol, rich platforms** — permission models, billing, and enterprise policy stay in platform implementations.
5. **Open participation** — anyone may propose spec changes via the contribution process.

## Roles

| Role | Responsibility |
|------|----------------|
| **Maintainers** | Merge contributions, cut releases, steward spec clarity, represent the project in external alignment discussions |
| **Contributors** | Propose spec changes, schemas, bindings, examples, and tests via pull request |
| **Implementers** | Build compatible brokers, SDKs, and agents; report interoperability gaps |

### Current maintainers

| Name | Scope | Contact |
|------|-------|---------|
| Brynn Jocelyn | Spec, schemas, Python reference SDK | via repository issues |

As additional implementers adopt ESP, we will expand maintainership to include at least one representative from a second organization before pursuing Linux Foundation or AAIF hosting.

## Decision making

### Specification changes

Normative changes require:

1. A pull request updating `SPEC.md` and any affected `schemas/`
2. A short rationale in the PR description (problem, proposed behavior, compatibility impact)
3. Approval from at least one maintainer
4. For breaking changes (`esp_version` major bump): 7-day review period on the PR before merge

Non-normative changes (examples, SDK improvements, documentation) follow the same PR process but may merge with a single maintainer approval.

### Release process

ESP uses semantic versioning on `esp_version`:

| Bump | When |
|------|------|
| **Major** | Breaking envelope or ensemble schema changes |
| **Minor** | New optional fields, patterns, or bindings |
| **Patch** | Clarifications, non-normative doc fixes |

Release artifacts:

- Tagged git release
- Updated JSON schemas
- Changelog entry in the release notes

### Escalation

Disagreements on normative behavior are resolved as follows:

1. Discussion on the pull request or issue
2. Maintainer decision documented in the PR thread
3. If unresolved, opening a dedicated design issue with a 14-day comment period
4. Final maintainer vote; dissenting opinions recorded in the issue

## Intellectual property

- All contributions are licensed under [Apache-2.0](LICENSE).
- Contributors certify they have the right to submit their work (see `CONTRIBUTING.md`).
- The project name **Ensemble Protocol** and identifier **ESP** are used descriptively; trademark transfer to a foundation would occur only through a formal contribution agreement if the project is donated.

## Alignment with external standards

ESP intentionally aligns with:

- [A2A](https://a2a-protocol.org) — task and message payloads
- [AGNTCY SLIM](https://slim.agntcy.org) — group transport
- [AGNTCY Collaboration Context RFC](https://github.com/agntcy/slim-spec/issues/14) — cross-org lifecycle and membership headers

Alignment proposals live in `docs/`. Maintainers participate in external RFC discussions but do not unilaterally bind ESP to draft specs without a recorded decision here.

## Path to neutral governance

This project is pre-foundation. Before applying to the [Agentic AI Foundation](https://aaif.io) or AGNTCY, we intend to satisfy:

- [ ] Two or more independent implementations
- [ ] Multi-organization contributor base
- [ ] Documented security and interoperability test suite
- [ ] Published 6–12 month roadmap
- [ ] Production adoption references (may be anonymized)

See `docs/alignment-agntcy-collaboration-context.md` for the current AGNTCY alignment proposal.

## Code of conduct

Participants are expected to follow the [Linux Foundation Code of Conduct](https://lfprojects.org/policies/code-of-conduct/) in all project spaces.