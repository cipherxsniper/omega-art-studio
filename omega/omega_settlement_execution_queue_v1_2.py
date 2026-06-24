#!/usr/bin/env python3

import sqlite3
import hashlib
import json
from datetime import datetime, timezone

DB_PATH = "/data/data/com.termux/files/home/Omega-Production/omega_bank/omega_ledger.db"

VALID_QUEUE_STATES = {
    "QUEUED",
    "EXECUTING",
    "RETRY_PENDING",
    "EXECUTED",
    "FAILED"
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def deterministic_hash(payload):
    normalized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(normalized.encode()).hexdigest()


def connect():
    return sqlite3.connect(DB_PATH)


def initialize_tables(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settlement_execution_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        queue_id TEXT UNIQUE,
        settlement_event_id TEXT,
        queue_priority INTEGER,
        retry_count INTEGER,
        execution_state TEXT,
        deterministic_queue_hash TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settlement_execution_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        queue_id TEXT,
        previous_state TEXT,
        new_state TEXT,
        transition_reason TEXT,
        transition_hash TEXT,
        created_at TEXT
    )
    """)


def run():
    conn = connect()
    cur = conn.cursor()

    initialize_tables(cur)

    conn.commit()

    print("📦 OMEGA SETTLEMENT EXECUTION QUEUE v1")
    print("QUEUE_INFRASTRUCTURE_READY")

    conn.close()


if __name__ == "__main__":
    run()
