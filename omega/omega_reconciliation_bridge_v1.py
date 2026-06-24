#!/usr/bin/env python3

import json
import sqlite3

DB = "omega_ledger.db"


def fetch_internal(cur):
    cur.execute("""
        SELECT id, type, payload, timestamp
        FROM ledger_events
        ORDER BY rowid ASC
    """)
    return cur.fetchall()


def fetch_external_simulated():
    # Stripe bridge simulation input (replace later with real webhook stream)
    return [
        {
            "id": "stripe_test_1",
            "type": "TX_SETTLED",
            "payload": {"amount": 250000.0},
            "source": "stripe"
        }
    ]


def normalize(row):
    id_, type_, payload, ts = row
    return {
        "id": id_,
        "type": type_,
        "payload": payload,
        "source": "internal"
    }


def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    internal = [normalize(r) for r in fetch_internal(cur)]
    external = fetch_external_simulated()

    print("🔁 OMEGA RECONCILIATION BRIDGE v1")

    internal_ids = {e["id"] for e in internal}

    for ext in external:
        if ext["id"] not in internal_ids:
            print({
                "id": ext["id"],
                "issue": "MISSING_INTERNAL"
            })

    print("✔ bridge scan complete")


if __name__ == "__main__":
    run()
