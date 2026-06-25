import pytest

from ensemble_protocol.ids import make_ensemble_id, parse_ensemble_id


def test_ensemble_id_roundtrip():
    eid = make_ensemble_id("bknight.dev", "invoice-delivery-2026-06-25")
    assert eid == "ens://bknight.dev/invoice-delivery-2026-06-25"
    ns, name = parse_ensemble_id(eid)
    assert ns == "bknight.dev"
    assert name == "invoice-delivery-2026-06-25"


def test_invalid_ensemble_id():
    with pytest.raises(ValueError):
        parse_ensemble_id("not-an-ensemble-id")
    with pytest.raises(ValueError):
        make_ensemble_id("", "name")