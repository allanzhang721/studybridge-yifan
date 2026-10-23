"""Read-only, operator-maintained public ledger, separate from sandbox orders."""
import csv
import io
import json
from urllib.parse import urlparse

from .engine import digest
from .storage import ROOT


def load_ledger(path=None) -> dict:
    path = path or ROOT / "data" / "public_ledger.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = set()
    for batch in data["batches"]:
        if batch["id"] in ids:
            raise ValueError("Duplicate ledger batch.")
        ids.add(batch["id"])
        for key in ("eligible_orders", "pledge_per_order_cents", "adjustment_cents", "sent_cents"):
            if type(batch[key]) is not int:
                raise ValueError("Ledger amounts must use integer cents.")
        accrued = batch["eligible_orders"]*batch["pledge_per_order_cents"]+batch["adjustment_cents"]
        if min(batch["eligible_orders"], batch["pledge_per_order_cents"], batch["sent_cents"], accrued) < 0 or batch["sent_cents"] > accrued:
            raise ValueError("The ledger does not reconcile.")
        if batch["sent_cents"] and not batch.get("receipt_url"):
            raise ValueError("A transferred amount needs a public receipt link.")
        if batch.get("recipient_confirmed") and not batch.get("confirmation_url"):
            raise ValueError("Recipient confirmation needs its own evidence.")
        for key in ("receipt_url", "confirmation_url", "report_url", "project_url"):
            value = batch.get(key)
            if value and (urlparse(value).scheme != "https" or not urlparse(value).netloc):
                raise ValueError("Evidence links must be HTTPS URLs.")
        batch["accrued_cents"] = accrued
        batch["outstanding_cents"] = accrued-batch["sent_cents"]
    return data


def totals(ledger: dict) -> dict:
    return {key: sum(b[key] for b in ledger["batches"]) for key in ("accrued_cents", "sent_cents", "outstanding_cents")}


def csv_bytes(rows: list[dict]) -> bytes:
    output = io.StringIO()
    if rows:
        fields = list(dict.fromkeys(k for row in rows for k in row))
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            # Neutralize spreadsheet formulas in user-supplied labels.
            writer.writerow({k: "'"+v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v for k, v in row.items()})
    else:
        output.write("batch_id,eligible_orders,accrued_cents,sent_cents,outstanding_cents\n")
    return output.getvalue().encode("utf-8-sig")

