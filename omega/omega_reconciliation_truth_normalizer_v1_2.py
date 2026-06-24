#!/usr/bin/env python3

import sqlite3
import json
import hashlib

DB = "omega_ledger.db"


def canonicalize(payload):
    """
    Ensures deterministic representation for financial truth validation
    """
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except:
            payload = {"raw": payload}

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def hash_event(payload):
    canonical = canonicalize(payload)
    return hashlib.sha256(canonical.encode()).hexdigest()


def run():
    print("🧠 OMEGA RECONCILIATION TRUTH NORMALIZER v1")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, payload, type, timestamp
        FROM ledger_events
        ORDER BY timestamp DESC
        LIMIT 20
    """)

    rows = cur.fetchall()

    normalized = []
    mismatches = []

    for r in rows:
        event_id, payload, event_type, ts = r

        try:
            parsed = json.loads(payload)
        except:
            parsed = {"raw": payload}

        canonical_hash = hash_event(parsed)
        raw_hash = hashlib.sha256(str(payload).encode()).hexdigest()

        if canonical_hash != raw_hash:
            mismatches.append(event_id)

        normalized.append({
            "event_id": event_id,
            "canonical_hash": canonical_hash
        })

    result = {
        "total_events": len(rows),
        "canonical_mismatches": len(mismatches),
        "system_state": "CANONICALIZED",
        "deterministic": len(mismatches) == 0
    }

    print(json.dumps(result, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
