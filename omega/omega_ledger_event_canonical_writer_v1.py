#!/usr/bin/env python3
"""
=========================================================
OMEGA LEDGER EVENT CANONICAL WRITER v1
Single Source of Truth Event Ingestion Layer
=========================================================
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "omega_ledger.db"


CAPITALIZATION_INIT_EVENT = {
    "event_type": "CAPITALIZATION_INIT",
    "event_id": "cap_init_001",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "currency": "USD",
    "ledger_effect": {
        "OMEGA_TREASURY": -13300000000.0,
        "OMEGA_CREDIT": 600000000.0,
        "OMEGA_RESERVE": 750000000.0,
        "OMEGA_INVESTMENT": 250000000.0,
        "THOMAS_LH": 50000000.0
    }
}


def compute_hash(event: dict) -> str:
    canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def ensure_table(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ledger_events (
        id TEXT PRIMARY KEY,
        type TEXT,
        payload TEXT,
        timestamp TEXT,
        event_hash TEXT
    )
    """)


def insert_event(cur, event):
    event_hash = compute_hash(event)

    cur.execute("""
        INSERT OR IGNORE INTO ledger_events
        (id, type, payload, timestamp, event_hash)
        VALUES (?, ?, ?, ?, ?)
    """, (
        event["event_id"],
        event["event_type"],
        json.dumps(event),
        event["timestamp"],
        event_hash
    ))

    return event_hash


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    ensure_table(cur)

    event = CAPITALIZATION_INIT_EVENT
    event_hash = insert_event(cur, event)

    conn.commit()
    conn.close()

    print("🧠 CAPITALIZATION EVENT WRITTEN")
    print({
        "event_id": event["event_id"],
        "hash": event_hash,
        "currency": event["currency"]
    })


if __name__ == "__main__":
    run()
