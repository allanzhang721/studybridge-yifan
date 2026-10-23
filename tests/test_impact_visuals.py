from copy import deepcopy
from pathlib import Path

from streamlit.testing.v1 import AppTest

from studybridge.impact_visuals import example_chain, fingerprint, verify_chain
from studybridge.ledger import load_ledger


def test_proof_detects_edits_reordering_and_truncation():
    original = example_chain()
    root = original[-1]["hash"]
    assert verify_chain(original, root)["valid"]
    changed = deepcopy(original)
    changed[0]["payload"]["allocation_cents"] = 37000
    result = verify_chain(changed, root)
    assert not result["valid"] and not result["records"][0]
    assert result["root_matches"]  # An unchanged last hash alone is insufficient.
    assert not verify_chain(original[:-1], root)["valid"]
    assert not verify_chain(list(reversed(original)), root)["valid"]
    assert not verify_chain([], root)["valid"]


def test_rewritten_chain_is_detected_against_original_reference():
    chain = example_chain()
    root = chain[-1]["hash"]
    chain[0]["payload"]["allocation_cents"] = 37000
    previous = "0" * 64
    for entry in chain:
        entry["previous_hash"] = previous
        entry["hash"] = fingerprint({k: entry[k] for k in ("sequence", "previous_hash", "payload")})
        previous = entry["hash"]
    result = verify_chain(chain, root)
    assert all(result["records"])
    assert not result["root_matches"] and not result["valid"]


def test_proof_demo_does_not_modify_live_or_personal_records(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYBRIDGE_DB_PATH", str(tmp_path / "proof.sqlite"))
    before = load_ledger()
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    app.button(key="nav_Impact ledger").click().run()
    assert not app.exception
    assert any(t.label == "Blockchain & proof" for t in app.tabs)
    assert any("All three record hashes match" in s.value for s in app.success)
    app.radio(key="proof_demo_mode").set_value("Edit allocation").run()
    assert any("Edit detected" in e.value for e in app.error)
    app.radio(key="proof_demo_mode").set_value("Rewrite the chain").run()
    assert any("Rewrite detected" in e.value for e in app.error)
    app.radio(key="proof_demo_mode").set_value("Original example").run()
    assert not app.exception
    assert not app.session_state["workspace"]["sandbox_orders"]
    assert load_ledger() == before
