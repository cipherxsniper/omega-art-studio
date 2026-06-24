#!/usr/bin/env python3

import sqlite3
import hashlib
import json
from datetime import datetime, timezone

DB_PATH = "/data/data/com.termux/files/home/Omega-Production/omega_bank/omega_ledger.db"


def utc_iso():
    return datetime.now(timezone.utc).isoformat()


def deterministic_hash(payload):
    normalized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(normalized.encode()).hexdigest()


def connect():
    return sqlite3.connect(DB_PATH)


def initialize_tables(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS runtime_health_orchestrator (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        orchestrator_id TEXT UNIQUE,
        queue_health TEXT,
        runtime_stability TEXT,
        congestion_level TEXT,
        operational_status TEXT,
        deterministic_runtime_hash TEXT,
        created_at TEXT
    )
    """)


def calculate_runtime_health(cur):
    cur.execute("""
    SELECT COUNT(*)
    FROM settlement_execution_queue
    WHERE execution_state='QUEUED'
    """)

    queued = cur.fetchone()[0]

    if queued >= 100:
        congestion = "HIGH"
        status = "DEGRADED"
    elif queued >= 25:
        congestion = "MEDIUM"
        status = "WARNING"
    else:
        congestion = "LOW"
        status = "HEALTHY"

    payload = {
        "queued_items": queued,
        "congestion": congestion,
        "status": status
    }

    runtime_hash = deterministic_hash(payload)

    cur.execute("""
    INSERT OR IGNORE INTO runtime_health_orchestrator (
        orchestrator_id,
        queue_health,
        runtime_stability,
        congestion_level,
        operational_status,
        deterministic_runtime_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        runtime_hash,
        "DETERMINISTIC_QUEUE_HEALTH",
        "STABLE",
        congestion,
        status,
        runtime_hash,
        utc_iso()
    ))

    return payload


def run():
    conn = connect()
    cur = conn.cursor()

    initialize_tables(cur)

    result = calculate_runtime_health(cur)

    conn.commit()

    print("🧠 OMEGA RUNTIME HEALTH ORCHESTRATOR v1")
    print(json.dumps(result, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
