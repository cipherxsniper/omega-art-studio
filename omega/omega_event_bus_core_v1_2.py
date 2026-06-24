#!/usr/bin/env python3

import os
import json
import uuid
import sqlite3
import hashlib
from datetime import datetime, UTC

DB_PATH = os.getenv("OMEGA_DB_PATH", "omega_ledger.db")


CANONICAL_EVENT_TYPES = {
    "MANUAL_CAPITAL_DISTRIBUTION",
    "MONTHLY_TREASURY_CYCLE",
    "STRIPE_PAYMENT",
    "CHAOS_TRANSACTION",
    "SETTLEMENT_EVENT"
}


def utc_now():
    return datetime.now(UTC).isoformat()


def connect_db():
    return sqlite3.connect(DB_PATH)


def ensure_schema(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ledger_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT UNIQUE,
        event_type TEXT,
        event_hash TEXT UNIQUE,
        parent_hash TEXT,
        payload_json TEXT,
        created_at TEXT
    )
    """)


def get_latest_hash(cur):
    cur.execute("""
    SELECT event_hash
    FROM ledger_events
    ORDER BY id DESC
    LIMIT 1
    """)
    row = cur.fetchone()
    return row[0] if row else "GENESIS"


def canonicalize_payload(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def generate_event_hash(parent_hash, payload_json):
    raw = f"{parent_hash}:{payload_json}"
    return hashlib.sha256(raw.encode()).hexdigest()


def validate_event(event):
    required = ["event_type", "currency", "ledger_effect"]

    for f in required:
        if f not in event:
            raise RuntimeError(f"Missing field: {f}")

    if event["event_type"] not in CANONICAL_EVENT_TYPES:
        raise RuntimeError("Invalid event type")

    if not isinstance(event["ledger_effect"], dict):
        raise RuntimeError("ledger_effect must be dict")


def insert_event(event):
    conn = connect_db()
    cur = conn.cursor()

    ensure_schema(cur)

    validate_event(event)

    parent_hash = get_latest_hash(cur)

    event.setdefault("event_id", str(uuid.uuid4()))
    event.setdefault("timestamp", utc_now())

    payload_json = canonicalize_payload(event)

    event_hash = generate_event_hash(parent_hash, payload_json)

    cur.execute("""
    INSERT INTO ledger_events (
        event_id,
        event_type,
        event_hash,
        parent_hash,
        payload_json,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        event["event_id"],
        event["event_type"],
        event_hash,
        parent_hash,
        payload_json,
        utc_now()
    ))

    conn.commit()
    conn.close()

    return {
        "event_id": event["event_id"],
        "event_hash": event_hash,
        "parent_hash": parent_hash
    }


def get_recent_events(limit=100):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT payload_json FROM ledger_events ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [json.loads(r[0]) for r in rows]


def get_event_count():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ledger_events")
    count = cur.fetchone()[0]
    conn.close()
    return count


# =========================
# SAFE SINGLE ENTRY EXPORT
# =========================

event_bus = type("EventBusProxy", (), {
    "insert_event": staticmethod(insert_event),
    "get_recent_events": staticmethod(get_recent_events),
    "get_event_count": staticmethod(get_event_count),
})()


if __name__ == "__main__":
    print("EVENT BUS READY")

# === COMPATIBILITY LAYER ===
def run():
    """
    Orchestrator entrypoint compatibility wrapper.
    Maps legacy import 'run' to actual event bus execution.
    """
    try:
        return main()
    except NameError:
        return start()
