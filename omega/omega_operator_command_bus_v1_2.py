#!/usr/bin/env python3

import sqlite3
import hashlib
import json
from datetime import datetime, timezone

DB_PATH = "/data/data/com.termux/files/home/Omega-Production/omega_bank/omega_ledger.db"

VALID_COMMANDS = {
    "FREEZE_SETTLEMENT",
    "UNFREEZE_SETTLEMENT",
    "ESCALATE_FRAUD",
    "OPEN_DISPUTE",
    "CLOSE_DISPUTE",
    "REQUEST_OPERATOR_REVIEW",
    "ACKNOWLEDGE_ALERT",
    "TRIGGER_RECOVERY"
}

VALID_STATUSES = {
    "PENDING",
    "AUTHORIZED",
    "EXECUTED",
    "REJECTED"
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
    CREATE TABLE IF NOT EXISTS operator_command_bus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        command_id TEXT UNIQUE,
        command_type TEXT,
        target_event_id TEXT,
        command_payload TEXT,
        command_status TEXT,
        authorized_by TEXT,
        deterministic_command_hash TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS operator_command_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        command_id TEXT,
        previous_status TEXT,
        new_status TEXT,
        transition_reason TEXT,
        transition_hash TEXT,
        created_at TEXT
    )
    """)


def create_command(
    cur,
    command_type,
    target_event_id,
    payload,
    authorized_by="OMEGA_SYSTEM"
):
    if command_type not in VALID_COMMANDS:
        raise ValueError("INVALID_COMMAND_TYPE")

    now = utc_now()

    command_payload = {
        "command_type": command_type,
        "target_event_id": target_event_id,
        "payload": payload,
        "authorized_by": authorized_by,
        "created_at": now
    }

    command_hash = deterministic_hash(command_payload)

    command_id = deterministic_hash({
        "target_event_id": target_event_id,
        "command_type": command_type,
        "timestamp": now
    })

    cur.execute("""
    INSERT INTO operator_command_bus (
        command_id,
        command_type,
        target_event_id,
        command_payload,
        command_status,
        authorized_by,
        deterministic_command_hash,
        created_at,
        updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        command_id,
        command_type,
        target_event_id,
        json.dumps(payload, sort_keys=True),
        "AUTHORIZED",
        authorized_by,
        command_hash,
        now,
        now
    ))

    transition_hash = deterministic_hash({
        "command_id": command_id,
        "transition": "PENDING->AUTHORIZED",
        "created_at": now
    })

    cur.execute("""
    INSERT INTO operator_command_history (
        command_id,
        previous_status,
        new_status,
        transition_reason,
        transition_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        command_id,
        "PENDING",
        "AUTHORIZED",
        "SYSTEM_AUTHORIZED",
        transition_hash,
        now
    ))

    return command_id


def run():
    conn = connect()
    cur = conn.cursor()

    initialize_tables(cur)

    conn.commit()

    print("🧭 OMEGA OPERATOR COMMAND BUS v1")
    print("COMMAND_BUS_READY")

    conn.close()


if __name__ == "__main__":
    run()
