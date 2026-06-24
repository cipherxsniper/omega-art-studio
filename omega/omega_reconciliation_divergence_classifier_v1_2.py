#!/usr/bin/env python3

import sqlite3
import json
import hashlib

DB = "omega_ledger.db"


def hash_payload(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def run():
    print("🧠 OMEGA RECONCILIATION DIVERGENCE CLASSIFIER v1")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # pull Stripe-style events from ledger
    cur.execute("""
        SELECT id, type, payload, timestamp
        FROM ledger_events
        ORDER BY timestamp DESC
        LIMIT 20
    """)

    rows = cur.fetchall()

    divergences = []

    for r in rows:
        event_id, event_type, payload, ts = r

        try:
            data = json.loads(payload)
        except:
            data = {}

        expected_hash = hash_payload(data)
        actual_hash = hashlib.sha256(str(payload).encode()).hexdigest()

        if expected_hash != actual_hash:
            divergences.append({
                "event_id": event_id,
                "type": "HASH_MISMATCH",
                "severity": "MEDIUM"
            })

    report = {
        "total_events": len(rows),
        "divergence_count": len(divergences),
        "divergences": divergences,
        "system_state": "CONSISTENT" if len(divergences) == 0 else "DEGRADED"
    }

    print(json.dumps(report, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
