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
    CREATE TABLE IF NOT EXISTS operational_policy_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_id TEXT UNIQUE,
        policy_type TEXT,
        target_id TEXT,
        policy_decision TEXT,
        severity TEXT,
        policy_reason TEXT,
        deterministic_policy_hash TEXT,
        created_at TEXT
    )
    """)


def evaluate_policy(cur):
    cur.execute("""
    SELECT COUNT(*)
    FROM operational_alerts
    WHERE severity='CRITICAL'
    """)

    critical_alerts = cur.fetchone()[0]

    if critical_alerts >= 3:
        severity = "CRITICAL"
        decision = "FREEZE_SETTLEMENT_EXECUTION"
    elif critical_alerts >= 1:
        severity = "WARNING"
        decision = "ESCALATE_OPERATOR_REVIEW"
    else:
        severity = "LOW"
        decision = "ALLOW_OPERATION"

    payload = {
        "critical_alerts": critical_alerts,
        "decision": decision,
        "severity": severity
    }

    policy_hash = deterministic_hash(payload)

    cur.execute("""
    INSERT OR IGNORE INTO operational_policy_decisions (
        policy_id,
        policy_type,
        target_id,
        policy_decision,
        severity,
        policy_reason,
        deterministic_policy_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        policy_hash,
        "RISK_THRESHOLD_POLICY",
        "SYSTEM_WIDE",
        decision,
        severity,
        "DETERMINISTIC_POLICY_EVALUATION",
        policy_hash,
        utc_iso()
    ))

    return payload


def run():
    conn = connect()
    cur = conn.cursor()

    initialize_tables(cur)

    result = evaluate_policy(cur)

    conn.commit()

    print("🛡 OMEGA OPERATIONAL POLICY ENGINE v1")
    print(json.dumps(result, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
