#!/usr/bin/env python3
"""
=========================================================
OMEGA REAL SETTLEMENT SIMULATOR v1
Stripe-like Financial Lifecycle Engine
=========================================================
"""

import sqlite3
import random
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent / "omega_ledger.db"

ACCOUNTS = [
    "OMEGA_CREDIT",
    "OMEGA_RESERVE",
    "OMEGA_INVESTMENT",
    "THOMAS_LH"
]


def now():
    return datetime.now(timezone.utc).isoformat()


def make_settlement_event():
    return {
        "id": str(uuid.uuid4()),
        "type": "SETTLEMENT_EVENT",
        "timestamp": now(),
        "payload": {
            "from": random.choice(ACCOUNTS),
            "to": random.choice(ACCOUNTS),
            "amount": round(random.uniform(1, 10000), 2),
            "status": random.choice(["PENDING", "SETTLED", "FAILED"]),
            "currency": "USD"
        }
    }


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("💳 OMEGA SETTLEMENT SIMULATOR v1 STARTING")

    # generate settlement flows
    for _ in range(30):
        e = make_settlement_event()
        cur.execute("""
            INSERT INTO ledger_events (id, type, payload, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            e["id"],
            e["type"],
            json.dumps(e["payload"]),
            e["timestamp"]
        ))

    conn.commit()
    conn.close()

    print("✅ SETTLEMENT EVENTS GENERATED")


if __name__ == "__main__":
    run()
