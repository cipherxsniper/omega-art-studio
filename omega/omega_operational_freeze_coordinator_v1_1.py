#!/usr/bin/env python3

import sqlite3
import json
import hashlib
from datetime import datetime, timezone

DB_PATH = "omega_ledger.db"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def sha256(data):
    return hashlib.sha256(data.encode()).hexdigest()

def ensure_tables(cur):

    cur.execute("""
    CREATE TABLE IF NOT EXISTS operational_freeze_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        freeze_id TEXT,
        target_event_id TEXT,
        freeze_status TEXT,
        severity TEXT,
        reason TEXT,
        recommendation TEXT,
        operator_override INTEGER DEFAULT 0,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS operational_freeze_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        history_id TEXT,
        freeze_id TEXT,
        target_event_id TEXT,
        action_type TEXT,
        action_reason TEXT,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

def fetch_freeze_recommendations(cur):

    cur.execute("""
    SELECT
        freeze_id,
        target_event_id,
        severity,
        reason,
        recommendation,
        deterministic_hash
    FROM operational_freeze_queue
    ORDER BY id ASC
    """)

    return cur.fetchall()

def freeze_exists(cur, freeze_id):

    cur.execute("""
    SELECT COUNT(*)
    FROM operational_freeze_state
    WHERE freeze_id = ?
    """, (freeze_id,))

    return cur.fetchone()[0] > 0

def persist_freeze_state(
    cur,
    freeze_id,
    target_event_id,
    severity,
    reason,
    recommendation,
    deterministic_hash
):

    cur.execute("""
    INSERT INTO operational_freeze_state (
        freeze_id,
        target_event_id,
        freeze_status,
        severity,
        reason,
        recommendation,
        deterministic_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        freeze_id,
        target_event_id,
        "ACTIVE_FREEZE",
        severity,
        reason,
        recommendation,
        deterministic_hash,
        utc_now()
    ))

def persist_history(
    cur,
    freeze_id,
    target_event_id,
    action_type,
    action_reason
):

    payload = {
        "freeze_id": freeze_id,
        "target_event_id": target_event_id,
        "action_type": action_type,
        "action_reason": action_reason
    }

    deterministic_hash = sha256(
        json.dumps(payload, sort_keys=True)
    )

    history_id = deterministic_hash[:24]

    cur.execute("""
    INSERT INTO operational_freeze_history (
        history_id,
        freeze_id,
        target_event_id,
        action_type,
        action_reason,
        deterministic_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        history_id,
        freeze_id,
        target_event_id,
        action_type,
        action_reason,
        deterministic_hash,
        utc_now()
    ))

def process_freeze(
    cur,
    freeze_id,
    target_event_id,
    severity,
    reason,
    recommendation,
    deterministic_hash
):

    if freeze_exists(cur, freeze_id):
        return False

    persist_freeze_state(
        cur,
        freeze_id,
        target_event_id,
        severity,
        reason,
        recommendation,
        deterministic_hash
    )

    persist_history(
        cur,
        freeze_id,
        target_event_id,
        "FREEZE_ACTIVATED",
        reason
    )

    return True

def run():

    conn = sqlite3.connect(DB_PATH)

    cur = conn.cursor()

    ensure_tables(cur)

    freeze_events = fetch_freeze_recommendations(cur)

    if not freeze_events:
        print("NO_FREEZE_RECOMMENDATIONS")
        conn.close()
        return

    activated = 0

    for (
        freeze_id,
        target_event_id,
        severity,
        reason,
        recommendation,
        deterministic_hash
    ) in freeze_events:

        result = process_freeze(
            cur,
            freeze_id,
            target_event_id,
            severity,
            reason,
            recommendation,
            deterministic_hash
        )

        if result:
            activated += 1

    conn.commit()

    print("🧊 OMEGA OPERATIONAL FREEZE COORDINATOR v1")
    print(f"FREEZE_EVENTS_PROCESSED={len(freeze_events)}")
    print(f"NEW_FREEZES_ACTIVATED={activated}")

    conn.close()

if __name__ == "__main__":
    run()
