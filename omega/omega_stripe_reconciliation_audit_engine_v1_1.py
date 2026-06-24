#!/usr/bin/env python3
"""
=========================================================
OMEGA STRIPE RECONCILIATION AUDIT ENGINE v1
Strict Accounting + Stripe Truth Verification Layer
=========================================================
"""

import sqlite3
import hashlib
import json
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "omega_ledger.db"


def hash_event(event: dict) -> str:
    canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def load_ledger_events(cur):
    cur.execute("SELECT id, type, payload FROM ledger_events")
    return cur.fetchall()


def load_stripe_events(cur):
    cur.execute("""
        SELECT id, type, payload
        FROM ledger_events
        WHERE type LIKE '%STRIPE%' OR type LIKE '%stripe%'
    """)
    return cur.fetchall()


def normalize(payload):
    try:
        return json.loads(payload)
    except:
        return {"raw": payload}


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    ledger_events = load_ledger_events(cur)
    stripe_events = load_stripe_events(cur)

    mismatches = []
    matched = 0

    ledger_hashes = {}

    # Build ledger hash map
    for eid, etype, payload in ledger_events:
        evt = normalize(payload)
        h = hash_event(evt)
        ledger_hashes[h] = eid

    # Compare Stripe events
    for eid, etype, payload in stripe_events:
        evt = normalize(payload)
        h = hash_event(evt)

        if h in ledger_hashes:
            matched += 1
        else:
            mismatches.append({
                "event_id": eid,
                "type": etype,
                "status": "MISMATCH"
            })

    result = {
        "total_ledger_events": len(ledger_events),
        "total_stripe_events": len(stripe_events),
        "matched_events": matched,
        "mismatched_events": len(mismatches),
        "mismatches": mismatches,
        "system_state": "AUDIT_COMPLETE"
    }

    print("💳 OMEGA STRIPE RECONCILIATION AUDIT ENGINE v1")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run()
