#!/usr/bin/env python3

import sqlite3
import json
import hashlib
from datetime import datetime, timezone

DB_PATH = "omega_ledger.db"

VALID_STATES = [
    "OPEN",
    "UNDER_REVIEW",
    "ESCALATED",
    "RESOLVED",
    "REJECTED"
]

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def sha256(data):
    return hashlib.sha256(data.encode()).hexdigest()

def ensure_tables(cur):

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settlement_dispute_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dispute_id TEXT,
        event_id TEXT,
        dispute_type TEXT,
        severity TEXT,
        current_state TEXT,
        payload TEXT,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settlement_dispute_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        history_id TEXT,
        dispute_id TEXT,
        previous_state TEXT,
        new_state TEXT,
        transition_reason TEXT,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

def dispute_exists(cur, dispute_id):

    cur.execute("""
    SELECT COUNT(*)
    FROM settlement_dispute_state
    WHERE dispute_id = ?
    """, (dispute_id,))

    return cur.fetchone()[0] > 0

def fetch_disputes(cur):

    cur.execute("""
    SELECT
        dispute_id,
        event_id,
        dispute_type,
        status,
        severity,
        payload,
        deterministic_hash
    FROM settlement_disputes
    ORDER BY id ASC
    """)

    return cur.fetchall()

def persist_state(
    cur,
    dispute_id,
    event_id,
    dispute_type,
    severity,
    payload,
    deterministic_hash
):

    cur.execute("""
    INSERT INTO settlement_dispute_state (
        dispute_id,
        event_id,
        dispute_type,
        severity,
        current_state,
        payload,
        deterministic_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dispute_id,
        event_id,
        dispute_type,
        severity,
        "OPEN",
        payload,
        deterministic_hash,
        utc_now()
    ))

def persist_history(
    cur,
    dispute_id,
    previous_state,
    new_state,
    transition_reason
):

    payload = {
        "dispute_id": dispute_id,
        "previous_state": previous_state,
        "new_state": new_state,
        "transition_reason": transition_reason
    }

    deterministic_hash = sha256(
        json.dumps(payload, sort_keys=True)
    )

    history_id = deterministic_hash[:24]

    cur.execute("""
    INSERT INTO settlement_dispute_history (
        history_id,
        dispute_id,
        previous_state,
        new_state,
        transition_reason,
        deterministic_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        history_id,
        dispute_id,
        previous_state,
        new_state,
        transition_reason,
        deterministic_hash,
        utc_now()
    ))

def process_dispute(
    cur,
    dispute_id,
    event_id,
    dispute_type,
    status,
    severity,
    payload,
    deterministic_hash
):

    if dispute_exists(cur, dispute_id):
        return False

    persist_state(
        cur,
        dispute_id,
        event_id,
        dispute_type,
        severity,
        payload,
        deterministic_hash
    )

    persist_history(
        cur,
        dispute_id,
        "NONE",
        "OPEN",
        "DISPUTE_CREATED"
    )

    return True

def run():

    conn = sqlite3.connect(DB_PATH)

    cur = conn.cursor()

    ensure_tables(cur)

    disputes = fetch_disputes(cur)

    if not disputes:
        print("NO_SETTLEMENT_DISPUTES")
        conn.close()
        return

    processed = 0

    for row in disputes:

        result = process_dispute(cur, *row)

        if result:
            processed += 1

    conn.commit()

    print("⚖️ OMEGA SETTLEMENT DISPUTE LIFECYCLE v1")
    print(f"DISPUTES_FOUND={len(disputes)}")
    print(f"NEW_DISPUTES_TRACKED={processed}")

    conn.close()

if __name__ == "__main__":
    run()
