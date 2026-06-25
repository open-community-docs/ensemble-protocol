import re

ENSEMBLE_ID_RE = re.compile(r"^ens://([^/]+)/([^/]+)$")


def make_ensemble_id(namespace: str, name: str) -> str:
    if not namespace or "/" in namespace:
        raise ValueError("namespace must be non-empty and must not contain '/'")
    if not name or "/" in name:
        raise ValueError("name must be non-empty and must not contain '/'")
    return f"ens://{namespace}/{name}"


def parse_ensemble_id(ensemble_id: str) -> tuple[str, str]:
    match = ENSEMBLE_ID_RE.match(ensemble_id)
    if not match:
        raise ValueError(f"invalid ensemble_id: {ensemble_id!r}")
    return match.group(1), match.group(2)