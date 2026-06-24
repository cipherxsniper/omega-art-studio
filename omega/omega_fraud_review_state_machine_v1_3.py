#!/usr/bin/env python3

import sqlite3
import json
import hashlib
from datetime import datetime, timezone

DB_PATH = "omega_ledger.db"

VALID_STATES = [
    "REVIEW_PENDING",
    "INVESTIGATING",
    "ESCALATED",
    "CONFIRMED_FRAUD",
    "CLEARED"
]

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def sha256(data):
    return hashlib.sha256(data.encode()).hexdigest()

def ensure_tables(cur):

    cur.execute("""
    CREATE TABLE IF NOT EXISTS fraud_review_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_id TEXT,
        event_id TEXT,
        severity TEXT,
        current_state TEXT,
        reason TEXT,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS fraud_review_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        history_id TEXT,
        review_id TEXT,
        previous_state TEXT,
        new_state TEXT,
        transition_reason TEXT,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

def review_exists(cur, review_id):

    cur.execute("""
    SELECT COUNT(*)
    FROM fraud_review_state
    WHERE review_id = ?
    """, (review_id,))

    return cur.fetchone()[0] > 0

def fetch_reviews(cur):

    cur.execute("""
    SELECT
        review_id,
        event_id,
        state,
        severity,
        reason,
        deterministic_hash
    FROM fraud_review_state_machine
    ORDER BY id ASC
    """)

    return cur.fetchall()

def persist_state(
    cur,
    review_id,
    event_id,
    severity,
    reason,
    deterministic_hash
):

    cur.execute("""
    INSERT INTO fraud_review_state (
        review_id,
        event_id,
        severity,
        current_state,
        reason,
        deterministic_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        review_id,
        event_id,
        severity,
        "REVIEW_PENDING",
        reason,
        deterministic_hash,
        utc_now()
    ))

def persist_history(
    cur,
    review_id,
    previous_state,
    new_state,
    transition_reason
):

    payload = {
        "review_id": review_id,
        "previous_state": previous_state,
        "new_state": new_state,
        "transition_reason": transition_reason
    }

    deterministic_hash = sha256(
        json.dumps(payload, sort_keys=True)
    )

    history_id = deterministic_hash[:24]

    cur.execute("""
    INSERT INTO fraud_review_history (
        history_id,
        review_id,
        previous_state,
        new_state,
        transition_reason,
        deterministic_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        history_id,
        review_id,
        previous_state,
        new_state,
        transition_reason,
        deterministic_hash,
        utc_now()
    ))

def process_review(
    cur,
    review_id,
    event_id,
    state,
    severity,
    reason,
    deterministic_hash
):

    if review_exists(cur, review_id):
        return False

    persist_state(
        cur,
        review_id,
        event_id,
        severity,
        reason,
        deterministic_hash
    )

    persist_history(
        cur,
        review_id,
        "NONE",
        "REVIEW_PENDING",
        "FRAUD_REVIEW_CREATED"
    )

    return True

def run():

    conn = sqlite3.connect(DB_PATH)

    cur = conn.cursor()

    ensure_tables(cur)

    reviews = fetch_reviews(cur)

    if not reviews:
        print("NO_FRAUD_REVIEWS")
        conn.close()
        return

    processed = 0

    for row in reviews:

        result = process_review(cur, *row)

        if result:
            processed += 1

    conn.commit()

    print("🚨 OMEGA FRAUD REVIEW STATE MACHINE v1")
    print(f"REVIEWS_FOUND={len(reviews)}")
    print(f"NEW_REVIEWS_TRACKED={processed}")

    conn.close()

if __name__ == "__main__":
    run()
