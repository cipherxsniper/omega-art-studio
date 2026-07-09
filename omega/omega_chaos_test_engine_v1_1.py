#!/usr/bin/env python3
"""
=========================================================
OMEGA CHAOS TEST ENGINE v1
Financial Stress + Stripe Simulation Layer
=========================================================
"""

import sqlite3
import random
import uuid
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent / "omega_ledger.db"


ACCOUNTS = [
    "OMEGA_TREASURY",
    "OMEGA_CREDIT",
    "OMEGA_RESERVE",
    "OMEGA_INVESTMENT",
    "THOMAS_LH"
]


def now():
    return datetime.now(timezone.utc).isoformat()


def make_event():
    amount = round(random.uniform(0.01, 5000.00), 2)

    from_acc = random.choice(ACCOUNTS)
    to_acc = random.choice([a for a in ACCOUNTS if a != from_acc])

    return {
        "event_id": str(uuid.uuid4()),
        "type": "CHAOS_TRANSFER",
        "timestamp": now(),
        "payload": {
            "from": from_acc,
            "to": to_acc,
            "amount": amount,
            "currency": "USD"
        }
    }


def hash_event(event):
    return hashlib.sha256(
        json.dumps(event, sort_keys=True).encode()
    ).hexdigest()


def apply_event(cur, event):
    cur.execute("""
        INSERT OR IGNORE INTO ledger_events
        (id, type, payload, timestamp, event_hash)
        VALUES (?, ?, ?, ?, ?)
    """, (
        event["event_id"],
        event["type"],
        json.dumps(event["payload"]),
        event["timestamp"],
        hash_event(event)
    ))


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("🧪 OMEGA CHAOS TEST ENGINE v1 STARTING")

    for _ in range(20):
        event = make_event()
        apply_event(cur, event)

    conn.commit()
    conn.close()

    print("✅ CHAOS TEST COMPLETE — EVENTS INJECTED")


if __name__ == "__main__":
    run()
