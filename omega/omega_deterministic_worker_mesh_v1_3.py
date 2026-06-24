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
    CREATE TABLE IF NOT EXISTS deterministic_worker_mesh (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id TEXT,
        execution_domain TEXT,
        coordination_state TEXT,
        lease_owner TEXT,
        lease_expiration TEXT,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

def build_worker_snapshot():
    payload = {
        "worker_id": "OMEGA_WORKER_001",
        "execution_domain": "SETTLEMENT_RUNTIME",
        "coordination_state": "ACTIVE",
        "lease_owner": "OMEGA_CORE",
        "lease_expiration": utc_now()
    }

    payload["deterministic_hash"] = deterministic_hash(payload)
    return payload

def persist(cur, payload):
    cur.execute("""
    INSERT INTO deterministic_worker_mesh (
        worker_id,
        execution_domain,
        coordination_state,
        lease_owner,
        lease_expiration,
        deterministic_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        payload["worker_id"],
        payload["execution_domain"],
        payload["coordination_state"],
        payload["lease_owner"],
        payload["lease_expiration"],
        payload["deterministic_hash"],
        utc_now()
    ))

def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    ensure_tables(cur)

    payload = build_worker_snapshot()

    persist(cur, payload)

    conn.commit()

    print("🕸 OMEGA DETERMINISTIC WORKER MESH v1")
    print(json.dumps(payload, indent=2))

    conn.close()

if __name__ == "__main__":
    run()
