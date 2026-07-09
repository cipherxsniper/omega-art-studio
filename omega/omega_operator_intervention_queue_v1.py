#!/usr/bin/env python3

import sqlite3
import json
import hashlib
from datetime import datetime, timezone

DB_PATH = "omega_ledger.db"

VALID_STATES = [
    "PENDING",
    "ACKNOWLEDGED",
    "IN_REVIEW",
    "ACTIONED",
    "RESOLVED",
    "REJECTED"
]

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def sha256(data):
    return hashlib.sha256(data.encode()).hexdigest()

def ensure_tables(cur):

    cur.execute("""
    CREATE TABLE IF NOT EXISTS operator_intervention_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        intervention_id TEXT,
        target_event_id TEXT,
        intervention_type TEXT,
        severity TEXT,
        current_state TEXT,
        payload TEXT,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS operator_intervention_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        history_id TEXT,
        intervention_id TEXT,
        previous_state TEXT,
        new_state TEXT,
        action_reason TEXT,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

def intervention_exists(cur, intervention_id):

    cur.execute("""
    SELECT COUNT(*)
    FROM operator_intervention_state
    WHERE intervention_id = ?
    """, (intervention_id,))

    return cur.fetchone()[0] > 0

def fetch_pending_queue(cur):

    cur.execute("""
    SELECT
        intervention_id,
        intervention_type,
        target_event_id,
        severity,
        payload,
        deterministic_hash,
        status
    FROM operator_intervention_queue
    ORDER BY id ASC
    """)

    return cur.fetchall()

def persist_state(
    cur,
    intervention_id,
    intervention_type,
    target_event_id,
    severity,
    payload,
    deterministic_hash
):

    cur.execute("""
    INSERT INTO operator_intervention_state (
        intervention_id,
        target_event_id,
        intervention_type,
        severity,
        current_state,
        payload,
        deterministic_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        intervention_id,
        target_event_id,
        intervention_type,
        severity,
        "PENDING",
        payload,
        deterministic_hash,
        utc_now()
    ))

def persist_history(
    cur,
    intervention_id,
    previous_state,
    new_state,
    action_reason
):

    payload = {
        "intervention_id": intervention_id,
        "previous_state": previous_state,
        "new_state": new_state,
        "action_reason": action_reason
    }

    deterministic_hash = sha256(
        json.dumps(payload, sort_keys=True)
    )

    history_id = deterministic_hash[:24]

    cur.execute("""
    INSERT INTO operator_intervention_history (
        history_id,
        intervention_id,
        previous_state,
        new_state,
        action_reason,
        deterministic_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        history_id,
        intervention_id,
        previous_state,
        new_state,
        action_reason,
        deterministic_hash,
        utc_now()
    ))

def process_intervention(
    cur,
    intervention_id,
    intervention_type,
    target_event_id,
    severity,
    payload,
    deterministic_hash,
    status
):

    if intervention_exists(cur, intervention_id):
        return False

    persist_state(
        cur,
        intervention_id,
        intervention_type,
        target_event_id,
        severity,
        payload,
        deterministic_hash
    )

    persist_history(
        cur,
        intervention_id,
        "NONE",
        "PENDING",
        "INITIAL_OPERATOR_ESCALATION"
    )

    return True

def run():

    conn = sqlite3.connect(DB_PATH)

    cur = conn.cursor()

    ensure_tables(cur)

    queue = fetch_pending_queue(cur)

    if not queue:
        print("NO_OPERATOR_INTERVENTIONS")
        conn.close()
        return

    processed = 0

    for row in queue:

        result = process_intervention(cur, *row)

        if result:
            processed += 1

    conn.commit()

    print("🧠 OMEGA OPERATOR INTERVENTION QUEUE v1")
    print(f"QUEUE_EVENTS={len(queue)}")
    print(f"NEW_INTERVENTIONS={processed}")

    conn.close()

if __name__ == "__main__":
    run()
