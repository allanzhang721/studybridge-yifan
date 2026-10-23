"""Operator-only local command line for reviewing ledger questions."""
import argparse
import json
from studybridge.storage import Store
from studybridge.ledger import load_ledger, totals

parser = argparse.ArgumentParser(description="StudyBridge local operator tools; never exposed in the learner UI.")
sub = parser.add_subparsers(dest="command", required=True)
sub.add_parser("validate-ledger")
sub.add_parser("pending")
reply = sub.add_parser("reply")
reply.add_argument("id", type=int)
reply.add_argument("--message", required=True)
args = parser.parse_args()
if args.command == "validate-ledger":
    ledger = load_ledger()
    print(json.dumps({"valid": True, "totals": totals(ledger)}, indent=2))
elif args.command == "pending":
    with Store().connect() as db:
        for row in db.execute("SELECT id,created,body FROM feedback WHERE status='pending' ORDER BY id"):
            print(json.dumps({"id": row[0], "created": row[1], "body": row[2]}, ensure_ascii=False))
else:
    Store().moderate(args.id, args.message)
    print("Platform reply appended. Question is now published without the username.")

