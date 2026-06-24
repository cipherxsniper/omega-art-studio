#!/usr/bin/env python3

import json
import hashlib
import sqlite3
from datetime import datetime, timezone

DB_PATH = "/data/data/com.termux/files/home/Omega-Production/omega_bank/omega_ledger.db"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def deterministic_hash(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()

def ensure_tables(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS infrastructure_checkpoints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        checkpoint_hash TEXT,
        checkpoint_state TEXT,
        rollback_ready INTEGER,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

def build_checkpoint():
    payload = {
        "checkpoint_state": "CHECKPOINT_CREATED",
        "rollback_ready": 1
    }

    payload["checkpoint_hash"] = deterministic_hash(payload)
    payload["deterministic_hash"] = deterministic_hash({
        "checkpoint_hash": payload["checkpoint_hash"]
    })

    return payload

def persist(cur, payload):
    cur.execute("""
    INSERT INTO infrastructure_checkpoints (
        checkpoint_hash,
        checkpoint_state,
        rollback_ready,
        deterministic_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        payload["checkpoint_hash"],
        payload["checkpoint_state"],
        payload["rollback_ready"],
        payload["deterministic_hash"],
        utc_now()
    ))

def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    ensure_tables(cur)

    payload = build_checkpoint()

    persist(cur, payload)

    conn.commit()

    print("💾 OMEGA INFRASTRUCTURE CHECKPOINT ORCHESTRATOR v1")
    print(json.dumps(payload, indent=2))

    conn.close()

if __name__ == "__main__":
    run()
