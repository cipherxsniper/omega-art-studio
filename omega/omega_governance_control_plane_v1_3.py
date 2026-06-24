#!/usr/bin/env python3

import os
import json
import uuid
import hashlib
import sqlite3

from datetime import datetime, timezone


DB_PATH = os.path.expanduser(
    "~/Omega-Production/omega_bank/omega_ledger.db"
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_hex(payload):
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True
        ).encode()
    ).hexdigest()


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables(cur):

    cur.execute("""
    CREATE TABLE IF NOT EXISTS governance_control_plane (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        governance_id TEXT UNIQUE,
        generated_at TEXT,
        operational_decision TEXT,
        severity TEXT,
        governance_state TEXT,
        governance_reason TEXT,
        subsystem_consensus TEXT,
        governance_lock_active INTEGER,
        deterministic_hash TEXT
    )
    """)


def safe_scalar(cur, query):

    try:
        cur.execute(query)
        row = cur.fetchone()

        if row is None:
            return 0

        return int(row[0])

    except Exception:
        return 0


def build_governance_snapshot(cur):

    critical_alerts = safe_scalar(
        cur,
        """
        SELECT COUNT(*)
        FROM operational_alerts
        WHERE severity='CRITICAL'
        """
    )

    freezes = safe_scalar(
        cur,
        """
        SELECT COUNT(*)
        FROM operational_freeze_state
        WHERE freeze_status='ACTIVE'
        """
    )

    fraud_reviews = safe_scalar(
        cur,
        """
        SELECT COUNT(*)
        FROM fraud_review_state
        """
    )

    recovery_events = safe_scalar(
        cur,
        """
        SELECT COUNT(*)
        FROM operational_recovery_state
        """
    )

    runtime_instability = safe_scalar(
        cur,
        """
        SELECT COUNT(*)
        FROM runtime_health_orchestrator
        WHERE operational_status!='HEALTHY'
        """
    )

    policy_blocks = safe_scalar(
        cur,
        """
        SELECT COUNT(*)
        FROM operational_policy_decisions
        WHERE policy_decision!='ALLOW_OPERATION'
        """
    )

    if freezes > 0:
        decision = "SYSTEM_FREEZE_COORDINATION"
        severity = "CRITICAL"
        state = "LOCKED"

    elif critical_alerts > 0:
        decision = "ESCALATE_OPERATIONAL_GOVERNANCE"
        severity = "HIGH"
        state = "ELEVATED"

    elif runtime_instability > 0:
        decision = "RUNTIME_STABILIZATION_REQUIRED"
        severity = "MEDIUM"
        state = "DEGRADED"

    elif policy_blocks > 0:
        decision = "POLICY_ENFORCEMENT_ACTIVE"
        severity = "MEDIUM"
        state = "RESTRICTED"

    else:
        decision = "ALLOW_OPERATION"
        severity = "LOW"
        state = "HEALTHY"

    governance_reason = {
        "critical_alerts": critical_alerts,
        "freezes": freezes,
        "fraud_reviews": fraud_reviews,
        "recovery_events": recovery_events,
        "runtime_instability": runtime_instability,
        "policy_blocks": policy_blocks
    }

    subsystem_consensus = {
        "alerts": critical_alerts,
        "freeze_coordination": freezes,
        "runtime_health": runtime_instability,
        "policy_enforcement": policy_blocks
    }

    payload = {
        "generated_at": utc_now(),
        "decision": decision,
        "severity": severity,
        "state": state,
        "reason": governance_reason,
        "subsystem_consensus": subsystem_consensus
    }

    payload["deterministic_hash"] = sha256_hex(payload)

    return payload


def persist_snapshot(cur, payload):

    cur.execute("""
    INSERT INTO governance_control_plane (
        governance_id,
        generated_at,
        operational_decision,
        severity,
        governance_state,
        governance_reason,
        subsystem_consensus,
        governance_lock_active,
        deterministic_hash
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        payload["generated_at"],
        payload["decision"],
        payload["severity"],
        payload["state"],
        json.dumps(payload["reason"], sort_keys=True),
        json.dumps(payload["subsystem_consensus"], sort_keys=True),
        1 if payload["state"] == "LOCKED" else 0,
        payload["deterministic_hash"]
    ))


def run():

    conn = connect_db()
    cur = conn.cursor()

    ensure_tables(cur)

    snapshot = build_governance_snapshot(cur)

    persist_snapshot(cur, snapshot)

    conn.commit()
    conn.close()

    print("🏛 OMEGA GOVERNANCE CONTROL PLANE v1")
    print(json.dumps(snapshot, indent=2))


if __name__ == "__main__":
    run()
