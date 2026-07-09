#!/usr/bin/env python3

import sqlite3
import json

DB = "omega_ledger.db"


def get_internal_events(cur):
    # SINGLE SOURCE OF TRUTH: SQLite ledger_events only
    cur.execute("""
        SELECT id, type, payload, timestamp
        FROM ledger_events
        ORDER BY rowid ASC
    """)
    return cur.fetchall()


def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    try:
        internal = get_internal_events(cur)
    except Exception as e:
        print("❌ RECONCILIATION FAILED:", str(e))
        return

    print("🔁 RECONCILIATION ENGINE v2 REPORT")

    for ev in internal:
        event_id, event_type, payload, timestamp = ev

        print({
            "id": event_id,
            "type": event_type,
            "payload": payload,
            "timestamp": timestamp,
            "issue": "MISSING_EXTERNAL"
        })


if __name__ == "__main__":
    run()
