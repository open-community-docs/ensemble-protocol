import json
from pathlib import Path

from ensemble_protocol import Ensemble


EXAMPLE = (
    Path(__file__).resolve().parents[3] / "examples" / "invoice-delivery" / "ensemble.json"
)


def test_invoice_delivery_example_loads():
    data = json.loads(EXAMPLE.read_text())
    ens = Ensemble.from_dict(data)
    assert ens.ensemble_id == "ens://bknight.dev/invoice-delivery-2026-06-25"
    assert ens.doc.coordinator == "financial-agent"
    refs = {m.agent_ref for m in ens.doc.members}
    assert refs == {"financial-agent", "document-agent", "email-agent"}