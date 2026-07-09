#!/usr/bin/env python3

import sqlite3
import json
import hashlib

DB = "omega_ledger.db"


def hash_state(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


def classify(mismatch_count):
    if mismatch_count == 0:
        return "ALLOW_OPERATION", "LOW"
    elif mismatch_count < 3:
        return "MONITOR", "MEDIUM"
    else:
        return "FREEZE_RECOMMEND", "HIGH"


def run():
    print("🧊 OMEGA FREEZE CONTROL PLANE v1")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) FROM ledger_events
    """)

    total = cur.fetchone()[0]

    cur.execute("""
        SELECT payload FROM ledger_events
        LIMIT 20
    """)

    rows = cur.fetchall()

    mismatch = 0

    for r in rows:
        if "{" not in str(r[0]):
            mismatch += 1

    decision, severity = classify(mismatch)

    state = {
        "total_events": total,
        "mismatch_count": mismatch,
        "decision": decision,
        "severity": severity
    }

    state["deterministic_hash"] = hash_state(state)

    print(json.dumps(state, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
