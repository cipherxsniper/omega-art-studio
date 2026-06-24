#!/usr/bin/env python3

import os
import json
import uuid
import hashlib
import sqlite3
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.expanduser("~/Omega-Production/omega_bank")
DB_PATH = os.path.join(BASE_DIR, "omega_ledger.db")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256d(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()


def connect_db():
    return sqlite3.connect(DB_PATH)


def ensure_tables(conn):
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS governance_lock_manager (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lock_id TEXT UNIQUE,
        governance_domain TEXT,
        lock_state TEXT,
        lock_reason TEXT,
        lease_owner TEXT,
        lock_expiration TEXT,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS governance_lock_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lock_id TEXT,
        previous_state TEXT,
        new_state TEXT,
        transition_reason TEXT,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

    conn.commit()


def fetch_existing_lock(cur, domain):
    cur.execute("""
    SELECT
        lock_id,
        lock_state
    FROM governance_lock_manager
    WHERE governance_domain=?
    ORDER BY id DESC
    LIMIT 1
    """, (domain,))
    return cur.fetchone()


def create_lock(cur, domain, reason):
    lock_id = str(uuid.uuid4())

    payload = {
        "lock_id": lock_id,
        "domain": domain,
        "state": "ACTIVE_LOCK",
        "reason": reason,
        "lease_owner": "OMEGA_GOVERNANCE_CORE",
        "expiration": (
            datetime.now(timezone.utc) + timedelta(minutes=15)
        ).isoformat()
    }

    deterministic_hash = sha256d(payload)

    cur.execute("""
    INSERT INTO governance_lock_manager (
        lock_id,
        governance_domain,
        lock_state,
        lock_reason,
        lease_owner,
        lock_expiration,
        deterministic_hash,
        created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lock_id,
        domain,
        "ACTIVE_LOCK",
        reason,
        "OMEGA_GOVERNANCE_CORE",
        payload["expiration"],
        deterministic_hash,
        utc_now()
    ))

    cur.execute("""
    INSERT INTO governance_lock_history (
        lock_id,
        previous_state,
        new_state,
        transition_reason,
        deterministic_hash,
        created_at
    ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        lock_id,
        "NONE",
        "ACTIVE_LOCK",
        reason,
        deterministic_hash,
        utc_now()
    ))

    return payload, deterministic_hash


def run():
    conn = connect_db()
    ensure_tables(conn)

    cur = conn.cursor()

    existing = fetch_existing_lock(cur, "SETTLEMENT_RUNTIME")

    if existing:
        print("🔒 OMEGA GOVERNANCE LOCK MANAGER v1")
        print("LOCK_INFRASTRUCTURE_READY")
        conn.close()
        return

    payload, deterministic_hash = create_lock(
        cur,
        "SETTLEMENT_RUNTIME",
        "INITIAL_GOVERNANCE_LOCK"
    )

    conn.commit()

    print("🔒 OMEGA GOVERNANCE LOCK MANAGER v1")
    print(json.dumps({
        "lock_id": payload["lock_id"],
        "governance_domain": payload["domain"],
        "lock_state": payload["state"],
        "deterministic_hash": deterministic_hash
    }, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
