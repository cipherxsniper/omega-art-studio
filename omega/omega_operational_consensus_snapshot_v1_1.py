#!/usr/bin/env python3

import sqlite3
import hashlib
import json
from datetime import datetime, timezone

DB_PATH = "/data/data/com.termux/files/home/Omega-Production/omega_bank/omega_ledger.db"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def deterministic_hash(payload):
    normalized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(normalized.encode()).hexdigest()


def connect():
    return sqlite3.connect(DB_PATH)


def initialize_tables(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS operational_consensus_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_hash TEXT UNIQUE,
        snapshot_payload TEXT,
        created_at TEXT
    )
    """)


def count(cur, table):
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]


def run():
    conn = connect()
    cur = conn.cursor()

    initialize_tables(cur)

    snapshot = {
        "generated_at": utc_now(),
        "operator_commands": count(cur, "operator_command_bus"),
        "execution_queue_items": count(cur, "settlement_execution_queue"),
        "alerts": count(cur, "operational_alerts"),
        "recoveries": count(cur, "operational_recovery_state"),
        "freezes": count(cur, "operational_freeze_state"),
        "fraud_reviews": count(cur, "fraud_review_state"),
        "disputes": count(cur, "settlement_dispute_state")
    }

    snapshot_hash = deterministic_hash(snapshot)

    cur.execute("""
    INSERT INTO operational_consensus_snapshots (
        snapshot_hash,
        snapshot_payload,
        created_at
    )
    VALUES (?, ?, ?)
    """, (
        snapshot_hash,
        json.dumps(snapshot, sort_keys=True),
        utc_now()
    ))

    conn.commit()

    print("📸 OMEGA OPERATIONAL CONSENSUS SNAPSHOT v1")
    print(json.dumps({
        "snapshot_hash": snapshot_hash,
        "snapshot": snapshot
    }, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
