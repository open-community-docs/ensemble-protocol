#!/usr/bin/env python3
"""Print ESP envelopes for the invoice-delivery coordination sequence.

Run from repo root:
    cd sdk/python && uv run python ../../examples/invoice-delivery/demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sdk" / "python"))

from ensemble_protocol import CoordinationPattern, Ensemble  # noqa: E402
from ensemble_protocol.models import Addressing, Payload  # noqa: E402

ENSEMBLE_PATH = Path(__file__).parent / "ensemble.json"


def main() -> None:
    data = json.loads(ENSEMBLE_PATH.read_text())
    ensemble = Ensemble.from_dict(data)

    steps = [
        (
            CoordinationPattern.UNICAST,
            Addressing.agent("document-agent"),
            Payload(
                intent="ingest_invoice_pdf",
                text="Ingest invoice document inv-1042.pdf",
                a2a_message={
                    "role": "user",
                    "parts": [{"text": "Ingest invoice document inv-1042.pdf"}],
                    "metadata": {
                        "skillId": "document.ingest",
                        "sourceRef": "invoice:1042",
                        "name": "inv-1042.pdf",
                        "mimeType": "application/pdf",
                    },
                },
            ),
            {"idempotency_key": "inv-1042-ingest"},
        ),
        (
            CoordinationPattern.UNICAST,
            Addressing.skill("send_document"),
            Payload(intent="deliver_invoice", text="Send invoice #1042 to client"),
            {"idempotency_key": "inv-1042-send"},
        ),
        (
            CoordinationPattern.UNICAST,
            Addressing.agent("email-agent"),
            Payload(intent="reconcile_delivery", text="Poll delivery status for task"),
            {},
        ),
    ]

    causation: str | None = None
    for pattern, to, payload, metadata in steps:
        envelope = ensemble.make_envelope(
            pattern,
            to=to,
            payload=payload,
            causation_id=causation,
            metadata=metadata,
        )
        causation = envelope.correlation_id
        print(json.dumps(envelope.to_dict(), indent=2))
        print()


if __name__ == "__main__":
    main()