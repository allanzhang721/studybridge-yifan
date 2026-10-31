"""Visual money trail and a local, explicitly simulated hash-chain demonstration."""
from copy import deepcopy
import hashlib
import html
import json

import streamlit as st


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def example_chain():
    events = [
        {"event": "Allocation", "batch": "DEMO-001", "eligible_orders": 90, "allocation_cents": 27000, "currency": "CNY"},
        {"event": "Transfer", "batch": "DEMO-001", "transferred_cents": 20000, "receipt": "Fictional receipt A; no real transfer", "currency": "CNY"},
        {"event": "Acknowledgement", "batch": "DEMO-001", "message": "Fictional recipient acknowledgement; not verified"},
    ]
    chain = []
    previous = "0" * 64
    for index, event in enumerate(events):
        record = {"sequence": index + 1, "previous_hash": previous, "payload": event}
        previous = fingerprint(record)
        chain.append({**record, "hash": previous})
    return chain


def verify_chain(chain, expected_root):
    previous, valid = "0" * 64, []
    for index, entry in enumerate(chain):
        record = {k: entry[k] for k in ("sequence", "previous_hash", "payload")}
        valid.append(entry["sequence"] == index + 1 and entry["previous_hash"] == previous
                     and entry["hash"] == fingerprint(record))
        previous = entry["hash"]
    return {"records": valid, "root_matches": bool(chain) and previous == expected_root,
            "valid": bool(chain) and all(valid) and previous == expected_root}


def trail(items):
    cards = []
    for number, (title, value, note) in enumerate(items, 1):
        cards.append(f'<div class="impact-node"><span class="impact-step">0{number}</span>'
                     f'<span class="impact-label">{html.escape(title)}</span><strong>{html.escape(value)}</strong>'
                     f'<p>{html.escape(note)}</p></div>')
    st.markdown('<div class="impact-trail">' + ''.join(cards) + '</div>', unsafe_allow_html=True)


def live_trail(ledger, total):
    batches = ledger["batches"]
    st.markdown('<div class="impact-status"><span class="impact-dot"></span> BLOCKCHAIN ANCHOR · NOT CONNECTED</div>', unsafe_allow_html=True)
    trail([
        ("Allocated", f"¥{total['accrued_cents']/100:,.2f}", "Live allocation after recorded adjustments"),
        ("Transferred", f"¥{total['sent_cents']/100:,.2f}", f"¥{total['outstanding_cents']/100:,.2f} awaiting transfer"),
        ("Receipt links", str(sum(bool(b.get('receipt_url')) for b in batches)), "Published evidence; not independently audited"),
        ("Recipient responses", str(sum(bool(b.get('recipient_confirmed')) for b in batches)), "Acknowledgements with separate evidence"),
    ])
    st.caption("Follow the record from allocation to acknowledgement. The current ledger is maintained locally; no transaction has been verified on a blockchain.")


def render_proof_demo():
    st.markdown("### Follow the money. Check the record.")
    st.caption("INTERACTIVE SIMULATION · Fictional figures and evidence · no wallet, network transaction or real donation")
    trail([
        ("Study packs", "100 × ¥29", "10 refunded → 90 eligible packs"),
        ("Education allocation", "¥270", "90 eligible packs × ¥3"),
        ("Example transfer", "¥200", "Fictional receipt and acknowledgement"),
        ("Still allocated", "¥70", "¥270 − ¥200; not yet transferred"),
    ])
    st.caption("Of the fictional ¥2,610 net sales, ¥270 is allocated to education; ¥2,340 is outside this allocation. These figures never enter the live ledger.")
    st.markdown("#### What happens if a record changes?")
    mode = st.radio("Try a record change", ["Original example", "Edit allocation", "Rewrite the chain"],
                    horizontal=True, key="proof_demo_mode")
    original = example_chain()
    expected_root = original[-1]["hash"]
    chain = deepcopy(original)
    if mode != "Original example":
        chain[0]["payload"]["allocation_cents"] = 37000
    if mode == "Rewrite the chain":
        previous = "0" * 64
        for entry in chain:
            entry["previous_hash"] = previous
            entry["hash"] = fingerprint({k: entry[k] for k in ("sequence", "previous_hash", "payload")})
            previous = entry["hash"]
    result = verify_chain(chain, expected_root)
    broken = False
    columns = st.columns(3)
    for col, entry, valid in zip(columns, chain, result["records"]):
        with col:
            broken = broken or not valid
            state = "Record changed" if not valid else "Earlier record changed" if broken else "Hash matches"
            style = "bad" if not valid else "pending" if broken or not result["root_matches"] else "good"
            st.markdown(f'<div class="proof-card {style}"><span class="impact-label">RECORD {entry["sequence"]}</span>'
                        f'<h4>{entry["payload"]["event"]}</h4><span class="proof-state">{state}</span>'
                        f'<p>Previous: <code>{entry["previous_hash"][:12]}…</code><br>Record: <code>{entry["hash"][:12]}…</code></p></div>', unsafe_allow_html=True)
    if result["valid"]:
        st.success("All three record hashes match, and the final fingerprint matches the saved example reference.")
    elif mode == "Edit allocation":
        st.error("Edit detected: ¥270 was changed to ¥370. The allocation no longer matches its recorded hash.")
    else:
        st.error("Rewrite detected against the original reference: the rebuilt records link correctly, but their final fingerprint is different.")
    st.caption("This check runs locally. Its saved reference is only a demonstration; it is not an independent or on-chain anchor.")

    with st.container(border=True):
        st.markdown("#### Where a blockchain would fit")
        st.markdown('''<div class="anchor-flow"><span>Publish the ledger snapshot</span><b>→</b><span>Hash the snapshot</span><b>→</b><span>Anchor hash on a network</span><b>→</b><span>Compare against the public transaction</span></div>''', unsafe_allow_html=True)
        st.write("An independently published reference makes a rewritten history easier to detect. A blockchain integration would need a real network, a confirmed transaction containing the hash, and a public explorer link.")
        st.caption("Current status: network not configured · transaction not submitted · explorer proof unavailable")
        st.write("A matching hash supports a claim that a record has not changed since anchoring. Receipts support payment claims; recipient acknowledgements support receipt claims; project reports describe how funds were used. A hash alone does not establish those facts.")
    with st.expander("Inspect the example proof"):
        st.caption("Saved example reference")
        st.code(expected_root, language=None)
        st.caption("Current final fingerprint")
        st.code(chain[-1]["hash"], language=None)
        st.json(chain)
        st.download_button("Download simulated proof", json.dumps({"simulation": True, "expected_root": expected_root,
                           "records": chain, "verification": result}, indent=2), "practilume-proof-demo.json", "application/json")
