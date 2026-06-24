#!/usr/bin/env python3

import sqlite3
import hashlib
import json
import time
from datetime import datetime, timezone, timedelta

DB_PATH = "/data/data/com.termux/files/home/Omega-Production/omega_bank/omega_ledger.db"

MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 30


def utc_now():
    return datetime.now(timezone.utc)


def utc_iso():
    return utc_now().isoformat()


def deterministic_hash(payload):
    normalized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(normalized.encode()).hexdigest()


def connect():
    return sqlite3.connect(DB_PATH)


def initialize_tables(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS execution_scheduler_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        schedule_id TEXT UNIQUE,
        queue_id TEXT,
        execution_priority INTEGER,
        retry_count INTEGER,
        next_execution_at TEXT,
        scheduler_state TEXT,
        scheduler_reason TEXT,
        deterministic_schedule_hash TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS execution_scheduler_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        schedule_id TEXT,
        previous_state TEXT,
        new_state TEXT,
        transition_reason TEXT,
        transition_hash TEXT,
        created_at TEXT
    )
    """)


def fetch_execution_queue(cur):
    cur.execute("""
    SELECT
        queue_id,
        queue_priority,
        retry_count,
        execution_state
    FROM settlement_execution_queue
    ORDER BY queue_priority DESC, id ASC
    """)

    return cur.fetchall()


def schedule_execution(cur, queue_item):
    queue_id, priority, retry_count, execution_state = queue_item

    now = utc_now()

    if retry_count is None:
        retry_count = 0

    backoff_seconds = BASE_BACKOFF_SECONDS * (2 ** retry_count)

    next_execution = now + timedelta(seconds=backoff_seconds)

    payload = {
        "queue_id": queue_id,
        "priority": priority,
        "retry_count": retry_count,
        "execution_state": execution_state,
        "next_execution": next_execution.isoformat()
    }

    schedule_hash = deterministic_hash(payload)

    schedule_id = deterministic_hash({
        "queue_id": queue_id,
        "timestamp": now.isoformat()
    })

    cur.execute("""
    INSERT OR IGNORE INTO execution_scheduler_state (
        schedule_id,
        queue_id,
        execution_priority,
        retry_count,
        next_execution_at,
        scheduler_state,
        scheduler_reason,
        deterministic_schedule_hash,
        created_at,
        updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        schedule_id,
        queue_id,
        priority,
        retry_count,
        next_execution.isoformat(),
        "SCHEDULED",
        "DETERMINISTIC_BACKOFF_COORDINATION",
        schedule_hash,
        now.isoformat(),
        now.isoformat()
    ))

    transition_hash = deterministic_hash({
        "schedule_id": schedule_id,
        "state": "SCHEDULED",
        "timestamp": now.isoformat()
    })

    cur.execute("""
    INSERT INTO execution_scheduler_history (
        schedule_id,
        previous_state,
        new_state,
        transition_reason,
        transition_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        schedule_id,
        "QUEUED",
        "SCHEDULED",
        "DETERMINISTIC_EXECUTION_WINDOW",
        transition_hash,
        now.isoformat()
    ))

    return {
        "schedule_id": schedule_id,
        "queue_id": queue_id,
        "next_execution": next_execution.isoformat(),
        "retry_count": retry_count
    }


def run():
    conn = connect()
    cur = conn.cursor()

    initialize_tables(cur)

    queue = fetch_execution_queue(cur)

    scheduled = []

    for item in queue:
        scheduled.append(schedule_execution(cur, item))

    conn.commit()

    print("⏱ OMEGA EXECUTION SCHEDULER v1")

    if not scheduled:
        print("NO_QUEUE_ITEMS_AVAILABLE")
    else:
        print(json.dumps(scheduled, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
