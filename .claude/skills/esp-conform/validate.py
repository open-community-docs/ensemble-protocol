#!/usr/bin/env python3
"""ESP conformance validator — checks ensemble documents and envelopes against
the JSON schemas in schemas/ and enforces key spec invariants from SPEC.md.

Usage:
    python validate.py ensemble path/to/ensemble.json
    python validate.py envelope path/to/envelope.json
    python validate.py ensemble '{"esp_version":"0.1.0", ...}'  # inline JSON
    python validate.py envelope '{"esp_version":"0.1.0", ...}'  # inline JSON

Exit codes: 0 = valid, 1 = validation errors found, 2 = usage/IO error.

Last Updated On: 2026-06-25
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Absolute path to schemas directory so this script works from any cwd.
REPO_ROOT = Path(__file__).resolve().parents[3]  # .../<repo>/.claude/skills/esp-conform/validate.py → repo root
SCHEMAS_DIR = REPO_ROOT / "schemas"

SCHEMA_FILES = {
    "ensemble": SCHEMAS_DIR / "ensemble.json",
    "member": SCHEMAS_DIR / "member.json",
    "envelope": SCHEMAS_DIR / "envelope.json",
}

# Valid enum values — duplicated here so the validator runs without the SDK.
VALID_ROLES = {"coordinator", "specialist", "observer", "broker"}
VALID_PATTERNS = {
    "broadcast", "unicast", "request_any", "request_all",
    "contract_net", "blackboard_post", "handoff",
}
VALID_STATES = {"proposed", "active", "suspended", "closing", "closed"}
VALID_PHASES = {"announce", "bid", "award", "reject"}
VALID_PERMISSIONS = {"read_blackboard", "post_artifacts", "respond_to_coordination", "coordinate"}

ENSEMBLE_ID_PREFIX = "ens://"
ENSEMBLE_ID_PARTS = 2  # namespace + name


def _try_import_jsonschema():
    """Return jsonschema module or None if not installed."""
    try:
        import jsonschema
        return jsonschema
    except ImportError:
        return None


def _load_schema(kind: str) -> dict:
    """Load and parse a JSON Schema file."""
    path = SCHEMA_FILES[kind]
    if not path.exists():
        raise FileNotFoundError(f"schema not found: {path}")
    return json.loads(path.read_text())


def _load_member_schema() -> dict:
    return _load_schema("member")


def validate_ensemble_id(eid: str) -> list[str]:
    """Return a list of error strings for a malformed ensemble_id."""
    errors: list[str] = []
    if not eid.startswith(ENSEMBLE_ID_PREFIX):
        errors.append(f"ensemble_id must start with 'ens://', got: {eid!r}")
        return errors
    rest = eid[len(ENSEMBLE_ID_PREFIX):]
    parts = rest.split("/")
    if len(parts) != ENSEMBLE_ID_PARTS or not all(parts):
        errors.append(
            f"ensemble_id must be 'ens://{{namespace}}/{{name}}' with exactly "
            f"two non-empty path segments, got: {eid!r}"
        )
    return errors


def check_ensemble_invariants(doc: dict) -> list[str]:
    """Enforce spec invariants beyond what the JSON Schema checks."""
    errors: list[str] = []

    # Coordinator must appear in members list with role coordinator.
    coordinator = doc.get("coordinator", "")
    members = doc.get("members", [])
    coordinator_members = [
        m for m in members
        if isinstance(m, dict) and m.get("agent_ref") == coordinator
    ]
    if not coordinator_members:
        errors.append(
            f"coordinator '{coordinator}' must be present in the members list "
            f"(SPEC.md §4.3: Coordinator MUST be declared at ensemble creation)"
        )
    else:
        coord_role = coordinator_members[0].get("role")
        if coord_role != "coordinator":
            errors.append(
                f"coordinator member '{coordinator}' has role '{coord_role}' "
                f"but must have role 'coordinator'"
            )

    # Validate each member's role and permissions.
    for i, m in enumerate(members):
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        if role and role not in VALID_ROLES:
            errors.append(f"members[{i}] role '{role}' is not a valid role (valid: {sorted(VALID_ROLES)})")
        for perm in m.get("permissions", []):
            if perm not in VALID_PERMISSIONS:
                errors.append(
                    f"members[{i}] permission '{perm}' is not valid "
                    f"(valid: {sorted(VALID_PERMISSIONS)})"
                )

    # State must be a valid lifecycle state.
    state = doc.get("state")
    if state and state not in VALID_STATES:
        errors.append(f"state '{state}' is not a valid lifecycle state (valid: {sorted(VALID_STATES)})")

    return errors


def check_envelope_invariants(env: dict) -> list[str]:
    """Enforce spec invariants on an ESP envelope."""
    errors: list[str] = []

    # Pattern must be valid.
    pattern = env.get("pattern")
    if pattern and pattern not in VALID_PATTERNS:
        errors.append(f"pattern '{pattern}' is not valid (valid: {sorted(VALID_PATTERNS)})")

    # contract_net requires payload.phase.
    payload = env.get("payload") or {}
    if pattern == "contract_net":
        phase = payload.get("phase")
        if not phase:
            errors.append("pattern 'contract_net' requires payload.phase (announce|bid|award|reject)")
        elif phase not in VALID_PHASES:
            errors.append(f"payload.phase '{phase}' is not valid (valid: {sorted(VALID_PHASES)})")

    # Selector format: must be "kind:value".
    to = env.get("to") or {}
    selector = to.get("selector", "")
    if selector:
        parts = selector.split(":", 1)
        valid_kinds = {"role", "agent", "skill", "all"}
        if len(parts) != 2 or parts[0] not in valid_kinds or not parts[1]:
            errors.append(
                f"to.selector '{selector}' must match '(role|agent|skill|all):value'"
            )
        # Observer targeting restriction.
        from_ = env.get("from") or {}
        if parts[0] == "role" and parts[1] == "observer" and pattern in ("request_any", "contract_net"):
            errors.append(
                f"observers MUST NOT be targeted by pattern '{pattern}' "
                f"(SPEC.md §4.3)"
            )

    # from.role must be valid.
    from_ = env.get("from") or {}
    from_role = from_.get("role")
    if from_role and from_role not in VALID_ROLES:
        errors.append(f"from.role '{from_role}' is not a valid role")

    return errors


def validate(kind: str, data: dict) -> tuple[list[str], list[str]]:
    """Return (schema_errors, invariant_errors)."""
    schema_errors: list[str] = []
    invariant_errors: list[str] = []

    # Always check ensemble_id format.
    eid = data.get("ensemble_id", "")
    if eid:
        invariant_errors.extend(validate_ensemble_id(eid))

    # JSON Schema validation (requires jsonschema package).
    js = _try_import_jsonschema()
    if js is not None:
        try:
            schema = _load_schema(kind)
            # Resolve $ref for member.json when validating ensemble.
            if kind == "ensemble":
                member_schema = _load_member_schema()
                resolver = js.RefResolver(
                    base_uri=SCHEMAS_DIR.as_uri() + "/",
                    referrer=schema,
                    store={
                        "member.json": member_schema,
                        str(SCHEMAS_DIR / "member.json"): member_schema,
                    },
                )
                validator_cls = js.validators.validator_for(schema)
                validator = validator_cls(schema, resolver=resolver)
            else:
                validator_cls = js.validators.validator_for(schema)
                validator = validator_cls(schema)

            for error in sorted(validator.iter_errors(data), key=lambda e: str(e.path)):
                path = ".".join(str(p) for p in error.absolute_path) or "(root)"
                schema_errors.append(f"{path}: {error.message}")
        except Exception as exc:
            schema_errors.append(f"[schema validation error] {exc}")
    else:
        schema_errors.append(
            "[jsonschema not installed] install with: pip install jsonschema; "
            "manual field checks will still run"
        )

    # Spec invariant checks (always run, no dependencies).
    if kind == "ensemble":
        invariant_errors.extend(check_ensemble_invariants(data))
    elif kind == "envelope":
        invariant_errors.extend(check_envelope_invariants(data))

    return schema_errors, invariant_errors


def main() -> int:
    """Entry point — returns exit code."""
    if len(sys.argv) < 3:
        print(
            "Usage: validate.py (ensemble|envelope) <path-or-json-string>",
            file=sys.stderr,
        )
        return 2

    kind = sys.argv[1].lower()
    if kind not in ("ensemble", "envelope"):
        print(f"Unknown kind '{kind}'. Use 'ensemble' or 'envelope'.", file=sys.stderr)
        return 2

    raw = sys.argv[2]

    # Try as file path first, then as inline JSON.
    path = Path(raw)
    try:
        if path.exists():
            text = path.read_text()
            source = str(path)
        else:
            text = raw
            source = "<inline>"
    except OSError:
        text = raw
        source = "<inline>"

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    schema_errors, invariant_errors = validate(kind, data)
    all_errors = schema_errors + invariant_errors

    print(f"Validating {kind} from {source}")
    print(f"esp_version: {data.get('esp_version', '(missing)')}")
    print(f"ensemble_id: {data.get('ensemble_id', '(missing)')}")
    print()

    if not all_errors:
        print("OK — no errors found.")
        return 0

    print(f"ERRORS ({len(all_errors)} found):")
    for i, err in enumerate(all_errors, 1):
        category = "[schema]" if i <= len(schema_errors) else "[invariant]"
        print(f"  {i}. {category} {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
