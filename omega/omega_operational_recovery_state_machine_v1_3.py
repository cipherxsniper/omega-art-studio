#!/usr/bin/env python3

import sqlite3
import json
import hashlib
from datetime import datetime, timezone

DB_PATH = "/data/data/com.termux/files/home/Omega-Production/omega_bank/omega_ledger.db"

RECOVERY_STATES = {
    "OPEN",
    "INVESTIGATING",
    "OPERATOR_REVIEW",
    "FREEZE_COORDINATION",
    "RECOVERY_IN_PROGRESS",
    "RECOVERED",
    "ESCALATED",
    "FAILED",
    "CLOSED"
}

SEVERITY_PRIORITY = {
    "INFO": 1,
    "WARNING": 2,
    "CRITICAL": 3,
    "FREEZE_RECOMMENDED": 4
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
    CREATE TABLE IF NOT EXISTS operational_recovery_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recovery_id TEXT UNIQUE,
        source_type TEXT,
        source_event_id TEXT,
        severity TEXT,
        current_state TEXT,
        recovery_reason TEXT,
        escalation_route TEXT,
        deterministic_recovery_hash TEXT,
        operator_required INTEGER,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS operational_recovery_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recovery_id TEXT,
        previous_state TEXT,
        new_state TEXT,
        transition_reason TEXT,
        transition_hash TEXT,
        created_at TEXT
    )
    """)


def fetch_operational_alerts(cur):
    columns = [row[1] for row in cur.execute("PRAGMA table_info(operational_alerts)")]

    if not columns:
        return []

    selectable = []

    for required in [
        "severity",
        "reason",
        "escalation_route",
        "deterministic_alert_hash",
        "target_event_id"
    ]:
        if required in columns:
            selectable.append(required)

    if "deterministic_alert_hash" not in selectable:
        selectable.append("'NO_HASH' AS deterministic_alert_hash")

    if "target_event_id" not in selectable:
        selectable.append("'UNKNOWN_EVENT' AS target_event_id")

    query = f"""
    SELECT {",".join(selectable)}
    FROM operational_alerts
    ORDER BY id ASC
    """

    cur.execute(query)

    rows = cur.fetchall()

    alerts = []

    for row in rows:
        obj = {}

        for idx, col in enumerate([
            x.strip().split(" AS ")[-1]
            for x in selectable
        ]):
            obj[col] = row[idx]

        alerts.append(obj)

    return alerts


def fetch_freeze_state(cur):
    cur.execute("""
    SELECT COUNT(*)
    FROM sqlite_master
    WHERE type='table'
    AND name='operational_freeze_state'
    """)

    exists = cur.fetchone()[0]

    if not exists:
        return []

    cur.execute("""
    SELECT
        freeze_status,
        severity,
        reason,
        target_event_id
    FROM operational_freeze_state
    ORDER BY id ASC
    """)

    rows = cur.fetchall()

    freeze_events = []

    for row in rows:
        freeze_events.append({
            "freeze_status": row[0],
            "severity": row[1],
            "reason": row[2],
            "target_event_id": row[3]
        })

    return freeze_events


def recovery_exists(cur, recovery_id):
    cur.execute("""
    SELECT COUNT(*)
    FROM operational_recovery_state
    WHERE recovery_id = ?
    """, (recovery_id,))

    return cur.fetchone()[0] > 0


def create_recovery_record(cur, payload):
    now = utc_now()

    recovery_hash = deterministic_hash(payload)

    cur.execute("""
    INSERT INTO operational_recovery_state (
        recovery_id,
        source_type,
        source_event_id,
        severity,
        current_state,
        recovery_reason,
        escalation_route,
        deterministic_recovery_hash,
        operator_required,
        created_at,
        updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        payload["recovery_id"],
        payload["source_type"],
        payload["source_event_id"],
        payload["severity"],
        payload["current_state"],
        payload["recovery_reason"],
        payload["escalation_route"],
        recovery_hash,
        payload["operator_required"],
        now,
        now
    ))

    transition_payload = {
        "recovery_id": payload["recovery_id"],
        "transition": "OPEN->INVESTIGATING",
        "reason": payload["recovery_reason"],
        "created_at": now
    }

    transition_hash = deterministic_hash(transition_payload)

    cur.execute("""
    INSERT INTO operational_recovery_history (
        recovery_id,
        previous_state,
        new_state,
        transition_reason,
        transition_hash,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        payload["recovery_id"],
        "OPEN",
        "INVESTIGATING",
        payload["recovery_reason"],
        transition_hash,
        now
    ))


def process_alerts(cur, alerts):
    created = 0

    for alert in alerts:
        severity = alert.get("severity", "INFO")

        if severity not in SEVERITY_PRIORITY:
            severity = "INFO"

        if SEVERITY_PRIORITY[severity] < 3:
            continue

        recovery_id = deterministic_hash({
            "target": alert.get("target_event_id"),
            "severity": severity,
            "reason": alert.get("reason")
        })

        if recovery_exists(cur, recovery_id):
            continue

        payload = {
            "recovery_id": recovery_id,
            "source_type": "ALERT",
            "source_event_id": alert.get("target_event_id"),
            "severity": severity,
            "current_state": "INVESTIGATING",
            "recovery_reason": alert.get("reason"),
            "escalation_route": alert.get(
                "escalation_route",
                "OPERATOR_REVIEW"
            ),
            "operator_required": 1
        }

        create_recovery_record(cur, payload)

        created += 1

    return created


def process_freezes(cur, freezes):
    created = 0

    for freeze in freezes:
        if freeze.get("freeze_status") != "ACTIVE":
            continue

        recovery_id = deterministic_hash({
            "freeze": freeze.get("target_event_id"),
            "severity": freeze.get("severity"),
            "reason": freeze.get("reason")
        })

        if recovery_exists(cur, recovery_id):
            continue

        payload = {
            "recovery_id": recovery_id,
            "source_type": "FREEZE",
            "source_event_id": freeze.get("target_event_id"),
            "severity": freeze.get("severity", "CRITICAL"),
            "current_state": "FREEZE_COORDINATION",
            "recovery_reason": freeze.get("reason"),
            "escalation_route": "FREEZE_COORDINATION",
            "operator_required": 1
        }

        create_recovery_record(cur, payload)

        created += 1

    return created


def run():
    conn = connect()
    cur = conn.cursor()

    initialize_tables(cur)

    alerts = fetch_operational_alerts(cur)
    freezes = fetch_freeze_state(cur)

    created_alert_recoveries = process_alerts(cur, alerts)
    created_freeze_recoveries = process_freezes(cur, freezes)

    conn.commit()

    total_created = (
        created_alert_recoveries +
        created_freeze_recoveries
    )

    print("🛠 OMEGA OPERATIONAL RECOVERY STATE MACHINE v1")

    if total_created == 0:
        print("NO_RECOVERY_ACTIONS_REQUIRED")
    else:
        print(json.dumps({
            "created_recovery_records": total_created,
            "alert_recoveries": created_alert_recoveries,
            "freeze_recoveries": created_freeze_recoveries
        }, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
