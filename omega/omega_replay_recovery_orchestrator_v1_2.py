#!/usr/bin/env python3

import sqlite3
import json
import hashlib
from datetime import datetime, timezone

DB_PATH = "omega_ledger.db"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def sha256(data):
    return hashlib.sha256(data.encode()).hexdigest()

def ensure_tables(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS replay_recovery_operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recovery_id TEXT,
        recovery_type TEXT,
        target_event_id TEXT,
        deterministic_hash TEXT,
        status TEXT,
        reason TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS operational_freeze_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        freeze_id TEXT,
        target_event_id TEXT,
        severity TEXT,
        reason TEXT,
        recommendation TEXT,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS operator_intervention_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        intervention_id TEXT,
        intervention_type TEXT,
        target_event_id TEXT,
        severity TEXT,
        payload TEXT,
        deterministic_hash TEXT,
        status TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settlement_disputes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dispute_id TEXT,
        event_id TEXT,
        dispute_type TEXT,
        status TEXT,
        severity TEXT,
        payload TEXT,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS fraud_review_state_machine (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_id TEXT,
        event_id TEXT,
        state TEXT,
        severity TEXT,
        reason TEXT,
        deterministic_hash TEXT,
        created_at TEXT
    )
    """)

def fetch_alerts(cur):

    cur.execute("PRAGMA table_info(operational_alerts)")
    cols = [c[1] for c in cur.fetchall()]

    severity_col = "severity"

    reason_col = "reason"

    route_col = (
        "escalation_route"
        if "escalation_route" in cols
        else "route"
    )

    hash_col = (
        "deterministic_hash"
        if "deterministic_hash" in cols
        else (
            "deterministic_alert_hash"
            if "deterministic_alert_hash" in cols
            else None
        )
    )

    if not hash_col:
        raise Exception(
            "NO_DETERMINISTIC_HASH_COLUMN_FOUND_IN_OPERATIONAL_ALERTS"
        )

    query = f"""
    SELECT
        {severity_col},
        {reason_col},
        {route_col},
        {hash_col}
    FROM operational_alerts
    ORDER BY id ASC
    """

    cur.execute(query)

    return cur.fetchall()

def persist_recovery(cur, recovery_type, target_event_id, reason):

    payload = {
        "recovery_type": recovery_type,
        "target_event_id": target_event_id,
        "reason": reason
    }

    deterministic_hash = sha256(
        json.dumps(payload, sort_keys=True)
    )

    recovery_id = deterministic_hash[:24]

    cur.execute("""
    INSERT INTO replay_recovery_operations (
        recovery_id,
        recovery_type,
        target_event_id,
        deterministic_hash,
        status,
        reason,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        recovery_id,
        recovery_type,
        target_event_id,
        deterministic_hash,
        "RECORDED",
        reason,
        utc_now()
    ))

def persist_freeze(cur, event_id, severity, reason):

    payload = {
        "event_id": event_id,
        "severity": severity,
        "reason": reason
    }

    deterministic_hash = sha256(
        json.dumps(payload, sort_keys=True)
    )

    freeze_id = deterministic_hash[:24]

    cur.execute("""
    INSERT INTO operational_freeze_queue (
        freeze_id,
        target_event_id,
        severity,
        reason,
        recommendation,
        deterministic_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        freeze_id,
        event_id,
        severity,
        reason,
        "FREEZE_RECOMMENDED",
        deterministic_hash,
        utc_now()
    ))

def persist_intervention(
    cur,
    intervention_type,
    event_id,
    severity,
    payload
):

    deterministic_hash = sha256(
        json.dumps(payload, sort_keys=True)
    )

    intervention_id = deterministic_hash[:24]

    cur.execute("""
    INSERT INTO operator_intervention_queue (
        intervention_id,
        intervention_type,
        target_event_id,
        severity,
        payload,
        deterministic_hash,
        status,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        intervention_id,
        intervention_type,
        event_id,
        severity,
        json.dumps(payload, sort_keys=True),
        deterministic_hash,
        "PENDING",
        utc_now()
    ))

def persist_dispute(
    cur,
    event_id,
    dispute_type,
    severity,
    payload
):

    deterministic_hash = sha256(
        json.dumps(payload, sort_keys=True)
    )

    dispute_id = deterministic_hash[:24]

    cur.execute("""
    INSERT INTO settlement_disputes (
        dispute_id,
        event_id,
        dispute_type,
        status,
        severity,
        payload,
        deterministic_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dispute_id,
        event_id,
        dispute_type,
        "OPEN",
        severity,
        json.dumps(payload, sort_keys=True),
        deterministic_hash,
        utc_now()
    ))

def persist_fraud_review(
    cur,
    event_id,
    severity,
    reason
):

    payload = {
        "event_id": event_id,
        "severity": severity,
        "reason": reason
    }

    deterministic_hash = sha256(
        json.dumps(payload, sort_keys=True)
    )

    review_id = deterministic_hash[:24]

    cur.execute("""
    INSERT INTO fraud_review_state_machine (
        review_id,
        event_id,
        state,
        severity,
        reason,
        deterministic_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        review_id,
        event_id,
        "REVIEW_PENDING",
        severity,
        reason,
        deterministic_hash,
        utc_now()
    ))

def route_alert(
    cur,
    severity,
    reason,
    route,
    alert_hash
):

    event_id = alert_hash[:18]

    if severity == "CRITICAL":

        persist_freeze(
            cur,
            event_id,
            severity,
            reason
        )

        persist_intervention(
            cur,
            "CRITICAL_ESCALATION",
            event_id,
            severity,
            {
                "reason": reason,
                "route": route
            }
        )

    if "FRAUD" in reason.upper():

        persist_fraud_review(
            cur,
            event_id,
            severity,
            reason
        )

    if "REPLAY" in reason.upper():

        persist_recovery(
            cur,
            "REPLAY_RECOVERY_REQUIRED",
            event_id,
            reason
        )

    if "SETTLEMENT" in reason.upper():

        persist_dispute(
            cur,
            event_id,
            "SETTLEMENT_DIVERGENCE",
            severity,
            {
                "reason": reason,
                "route": route
            }
        )

def run():

    conn = sqlite3.connect(DB_PATH)

    cur = conn.cursor()

    ensure_tables(cur)

    alerts = fetch_alerts(cur)

    if not alerts:
        print("NO_ALERTS_AVAILABLE")
        conn.close()
        return

    for severity, reason, route, alert_hash in alerts:

        route_alert(
            cur,
            severity,
            reason,
            route,
            alert_hash
        )

    conn.commit()

    print("🧠 OMEGA REPLAY RECOVERY ORCHESTRATOR v1")
    print(f"PROCESSED_ALERTS={len(alerts)}")

    conn.close()

if __name__ == "__main__":
    run()
