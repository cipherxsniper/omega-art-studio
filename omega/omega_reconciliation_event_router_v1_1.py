#!/usr/bin/env python3

import sqlite3
import json
import hashlib
from datetime import datetime, UTC

DB = "omega_ledger.db"

ANOMALY_RULES = {
    "MISSING_EXTERNAL": {
        "severity": "WARNING",
        "action": "send_to_reconciliation_queue",
    },
    "MISSING_INTERNAL": {
        "severity": "CRITICAL",
        "action": "freeze_candidate",
    },
    "DUPLICATE_SETTLEMENT": {
        "severity": "CRITICAL",
        "action": "fraud_review_required",
    },
    "REPLAY_CONFLICT": {
        "severity": "CRITICAL",
        "action": "fraud_review_required",
    },
    "HASH_DIVERGENCE": {
        "severity": "CRITICAL",
        "action": "freeze_candidate",
    },
    "FRAUD_SUSPECTED": {
        "severity": "CRITICAL",
        "action": "fraud_review_required",
    },
    "SETTLEMENT_DRIFT": {
        "severity": "WARNING",
        "action": "escalate_to_operator",
    }
}


def ensure_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reconciliation_router_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT,
            issue_type TEXT,
            severity TEXT,
            recommended_action TEXT,
            payload TEXT,
            created_at TEXT,
            deterministic_hash TEXT
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_router_event_id
        ON reconciliation_router_events(event_id)
    """)


def load_reconciliation_events():
    try:
        with open("reconciliation_report.json", "r") as f:
            return json.load(f)
    except Exception:
        return []


def deterministic_hash(data):
    encoded = json.dumps(data, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def already_processed(cur, event_id, issue_type):
    cur.execute("""
        SELECT 1
        FROM reconciliation_router_events
        WHERE event_id = ?
        AND issue_type = ?
        LIMIT 1
    """, (event_id, issue_type))

    return cur.fetchone() is not None


def classify_issue(issue_type):
    return ANOMALY_RULES.get(issue_type, {
        "severity": "INFO",
        "action": "monitor_only"
    })


def persist_router_event(cur, routed):
    cur.execute("""
        INSERT INTO reconciliation_router_events (
            event_id,
            issue_type,
            severity,
            recommended_action,
            payload,
            created_at,
            deterministic_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        routed["event_id"],
        routed["issue_type"],
        routed["severity"],
        routed["recommended_action"],
        json.dumps(routed["payload"], sort_keys=True),
        routed["created_at"],
        routed["deterministic_hash"]
    ))


def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    ensure_tables(cur)

    reconciliation_events = load_reconciliation_events()

    routed_events = []

    for item in reconciliation_events:

        event_id = item.get("id")
        issue_type = item.get("issue")

        if not event_id or not issue_type:
            continue

        if already_processed(cur, event_id, issue_type):
            continue

        classification = classify_issue(issue_type)

        routed = {
            "event_id": event_id,
            "issue_type": issue_type,
            "severity": classification["severity"],
            "recommended_action": classification["action"],
            "payload": item,
            "created_at": datetime.now(UTC).isoformat()
        }

        routed["deterministic_hash"] = deterministic_hash(routed)

        persist_router_event(cur, routed)

        routed_events.append(routed)

    conn.commit()
    conn.close()

    print("🧭 OMEGA RECONCILIATION EVENT ROUTER v1")

    if not routed_events:
        print("NO_NEW_ROUTING_EVENTS")
        return

    for event in routed_events:
        print(json.dumps(event, indent=2))


if __name__ == "__main__":
    run()

