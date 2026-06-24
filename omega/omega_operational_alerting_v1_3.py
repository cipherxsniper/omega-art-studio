#!/usr/bin/env python3

import sqlite3
import json
import hashlib
from datetime import datetime, UTC

DB_PATH = "omega_ledger.db"

ESCALATION_RULES = {
    "critical_anomalies": {
        "threshold": 1,
        "severity": "CRITICAL",
        "escalation_route": "freeze_candidate",
        "reason": "CRITICAL_ANOMALY_DETECTED"
    },

    "replay_conflicts": {
        "threshold": 1,
        "severity": "CRITICAL",
        "escalation_route": "operator_escalation",
        "reason": "REPLAY_CONFLICT_DETECTED"
    },

    "fraud_suspects": {
        "threshold": 1,
        "severity": "CRITICAL",
        "escalation_route": "fraud_review_required",
        "reason": "FRAUD_SIGNAL_DETECTED"
    },

    "missing_external": {
        "threshold": 1,
        "severity": "WARNING",
        "escalation_route": "reconciliation_review",
        "reason": "MISSING_EXTERNAL_TRUTH"
    },

    "missing_internal": {
        "threshold": 1,
        "severity": "WARNING",
        "escalation_route": "internal_consistency_review",
        "reason": "MISSING_INTERNAL_LEDGER"
    },

    "provider_divergence_count": {
        "threshold": 1,
        "severity": "CRITICAL",
        "escalation_route": "provider_divergence_review",
        "reason": "PROVIDER_DIVERGENCE_DETECTED"
    },

    "failed_settlements": {
        "threshold": 1,
        "severity": "WARNING",
        "escalation_route": "settlement_review",
        "reason": "FAILED_SETTLEMENT_DETECTED"
    }
}

def ensure_tables(cur):

    cur.execute("""
        CREATE TABLE IF NOT EXISTS operational_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_hash TEXT UNIQUE,
            metric_name TEXT,
            metric_value INTEGER,
            severity TEXT,
            escalation_route TEXT,
            reason TEXT,
            created_at TEXT,
            payload TEXT
        )
    """)

def get_latest_snapshot(cur):

    cur.execute("""
        SELECT payload
        FROM operational_health_snapshots
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    if not row:
        return None

    return json.loads(row[0])

def flatten_metrics(snapshot):

    flattened = {}

    for category in snapshot["metrics"].values():

        for key, value in category.items():
            flattened[key] = value

    return flattened

def deterministic_hash(payload):

    canonical = json.dumps(payload, sort_keys=True)

    return hashlib.sha256(
        canonical.encode()
    ).hexdigest()

def alert_exists(cur, alert_hash):

    cur.execute("""
        SELECT 1
        FROM operational_alerts
        WHERE alert_hash=?
    """, (alert_hash,))

    return cur.fetchone() is not None

def persist_alert(cur, payload, alert_hash):

    cur.execute("""
        INSERT INTO operational_alerts (
            alert_hash,
            metric_name,
            metric_value,
            severity,
            escalation_route,
            reason,
            created_at,
            payload
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alert_hash,
        payload["metric_name"],
        payload["metric_value"],
        payload["severity"],
        payload["escalation_route"],
        payload["reason"],
        payload["created_at"],
        json.dumps(payload, sort_keys=True)
    ))

def process_rules(cur, metrics):

    generated = []

    for metric_name, rule in ESCALATION_RULES.items():

        metric_value = metrics.get(metric_name, 0)

        if metric_value < rule["threshold"]:
            continue

        payload = {
            "metric_name": metric_name,
            "metric_value": metric_value,
            "severity": rule["severity"],
            "escalation_route": rule["escalation_route"],
            "reason": rule["reason"],
            "created_at": datetime.now(UTC).isoformat()
        }

        alert_hash = deterministic_hash(payload)

        if alert_exists(cur, alert_hash):
            continue

        persist_alert(cur, payload, alert_hash)

        generated.append({
            "alert_hash": alert_hash,
            **payload
        })

    return generated

def run():

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    ensure_tables(cur)

    snapshot = get_latest_snapshot(cur)

    if not snapshot:
        print("NO_OPERATIONAL_SNAPSHOTS")
        return

    metrics = flatten_metrics(snapshot)

    alerts = process_rules(cur, metrics)

    conn.commit()

    print("🚨 OMEGA OPERATIONAL ALERTING v1")

    if not alerts:
        print("NO_NEW_ALERTS")
    else:
        print(json.dumps(alerts, indent=2))

    conn.close()

if __name__ == "__main__":
    run()

