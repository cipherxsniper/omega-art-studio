#!/usr/bin/env python3

"""
=========================================================
OMEGA STRIPE REALITY INGESTION BRIDGE v1 (SCHEMA SAFE)
Fix: guaranteed table bootstrap before any execution
=========================================================
"""

import json
import hashlib
import sqlite3
from datetime import datetime, timezone

from omega_env_loader_v1 import get_db_path


# -----------------------------
# DB
# -----------------------------
def db():
    return sqlite3.connect(get_db_path())


# -----------------------------
# HASH
# -----------------------------
def event_hash(event: dict) -> str:
    raw = json.dumps(event, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


# -----------------------------
# BOOTSTRAP SCHEMA SAFELY
# -----------------------------
def bootstrap_schema(cur):

    cur.execute("""
    CREATE TABLE IF NOT EXISTS stripe_event_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT,
        event_type TEXT,
        payload TEXT,
        event_hash TEXT,
        status TEXT,
        created_at TEXT
    )
    """)


# -----------------------------
# STORE EVENT
# -----------------------------
def store_event(cur, event, status):

    h = event_hash(event)

    cur.execute("""
    INSERT INTO stripe_event_log (
        event_id,
        event_type,
        payload,
        event_hash,
        status,
        created_at
    ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        event.get("id", "unknown"),
        event.get("type", "unknown"),
        json.dumps(event),
        h,
        status,
        datetime.now(timezone.utc).isoformat()
    ))

    return h


# -----------------------------
# REPLAY CHECK
# -----------------------------
def validate_replay(cur, event):

    h = event_hash(event)

    cur.execute("""
    SELECT event_hash
    FROM stripe_event_log
    WHERE event_hash = ?
    LIMIT 1
    """, (h,))

    row = cur.fetchone()

    if row:
        return "REPLAY_MATCH"
    return "NEW_EVENT"


# -----------------------------
# MAIN
# -----------------------------
def run():

    conn = db()
    cur = conn.cursor()

    bootstrap_schema(cur)

    now = datetime.now(timezone.utc).isoformat()

    sample_event = {
        "id": "evt_test_001",
        "type": "payment_intent.succeeded",
        "amount": 5000,
        "currency": "usd",
        "status": "succeeded"
    }

    replay_status = validate_replay(cur, sample_event)

    event_h = store_event(cur, sample_event, replay_status)

    conn.commit()

    print("🌐 OMEGA STRIPE REALITY INGESTION BRIDGE v1 (SCHEMA SAFE)")
    print({
        "timestamp": now,
        "event_id": sample_event["id"],
        "replay_status": replay_status,
        "event_hash": event_h
    })

    conn.close()


if __name__ == "__main__":
    run()
