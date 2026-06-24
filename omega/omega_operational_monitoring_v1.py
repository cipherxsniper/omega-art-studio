#!/usr/bin/env python3

import sqlite3
import json
import hashlib
from datetime import datetime, UTC

DB_PATH = "omega_ledger.db"

def safe_count(cur, query):
    try:
        cur.execute(query)
        row = cur.fetchone()
        return row[0] if row else 0
    except Exception:
        return 0

def table_exists(cur, table_name):
    cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name=?
    """, (table_name,))
    return cur.fetchone() is not None

def collect_settlement_metrics(cur):
    metrics = {}

    if table_exists(cur, "events"):

        metrics["total_settlements"] = safe_count(
            cur,
            """
            SELECT COUNT(*)
            FROM events
            WHERE type='TX_SETTLED'
            """
        )

        metrics["pending_settlements"] = safe_count(
            cur,
            """
            SELECT COUNT(*)
            FROM events
            WHERE type='TX_REQUESTED'
            """
        )

    else:
        metrics["total_settlements"] = 0
        metrics["pending_settlements"] = 0

    metrics["failed_settlements"] = safe_count(
        cur,
        """
        SELECT COUNT(*)
        FROM payment_failures
        """
    ) if table_exists(cur, "payment_failures") else 0

    metrics["replay_conflicts"] = safe_count(
        cur,
        """
        SELECT COUNT(*)
        FROM reconciliation_events
        WHERE issue='REPLAY_CONFLICT'
        """
    ) if table_exists(cur, "reconciliation_events") else 0

    return metrics

def collect_reconciliation_metrics(cur):
    metrics = {}

    if not table_exists(cur, "reconciliation_events"):
        return {
            "missing_external": 0,
            "missing_internal": 0,
            "fraud_suspects": 0,
            "freeze_recommendations": 0
        }

    metrics["missing_external"] = safe_count(
        cur,
        """
        SELECT COUNT(*)
        FROM reconciliation_events
        WHERE issue='MISSING_EXTERNAL'
        """
    )

    metrics["missing_internal"] = safe_count(
        cur,
        """
        SELECT COUNT(*)
        FROM reconciliation_events
        WHERE issue='MISSING_INTERNAL'
        """
    )

    metrics["fraud_suspects"] = safe_count(
        cur,
        """
        SELECT COUNT(*)
        FROM reconciliation_events
        WHERE issue='FRAUD_SUSPECTED'
        """
    )

    metrics["freeze_recommendations"] = safe_count(
        cur,
        """
        SELECT COUNT(*)
        FROM reconciliation_router_events
        WHERE recommended_action='freeze_candidate'
        """
    ) if table_exists(cur, "reconciliation_router_events") else 0

    return metrics

def collect_router_metrics(cur):

    if not table_exists(cur, "reconciliation_router_events"):
        return {
            "critical_anomalies": 0,
            "warnings": 0,
            "escalation_count": 0
        }

    return {
        "critical_anomalies": safe_count(
            cur,
            """
            SELECT COUNT(*)
            FROM reconciliation_router_events
            WHERE severity='CRITICAL'
            """
        ),

        "warnings": safe_count(
            cur,
            """
            SELECT COUNT(*)
            FROM reconciliation_router_events
            WHERE severity='WARNING'
            """
        ),

        "escalation_count": safe_count(
            cur,
            """
            SELECT COUNT(*)
            FROM reconciliation_router_events
            WHERE route='escalate_to_operator'
            """
        )
    }

def collect_external_truth_metrics(cur):

    if not table_exists(cur, "external_truth_snapshots"):
        return {
            "persisted_snapshots": 0,
            "provider_divergence_count": 0
        }

    return {
        "persisted_snapshots": safe_count(
            cur,
            """
            SELECT COUNT(*)
            FROM external_truth_snapshots
            """
        ),

        "provider_divergence_count": safe_count(
            cur,
            """
            SELECT COUNT(*)
            FROM reconciliation_events
            WHERE issue LIKE '%EXTERNAL%'
            """
        ) if table_exists(cur, "reconciliation_events") else 0
    }

def build_health_snapshot(metrics):

    canonical = json.dumps(metrics, sort_keys=True)

    deterministic_hash = hashlib.sha256(
        canonical.encode()
    ).hexdigest()

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "deterministic_hash": deterministic_hash,
        "metrics": metrics
    }

def persist_snapshot(cur, snapshot):

    cur.execute("""
        CREATE TABLE IF NOT EXISTS operational_health_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at TEXT,
            deterministic_hash TEXT,
            payload TEXT
        )
    """)

    cur.execute("""
        INSERT INTO operational_health_snapshots (
            generated_at,
            deterministic_hash,
            payload
        )
        VALUES (?, ?, ?)
    """, (
        snapshot["generated_at"],
        snapshot["deterministic_hash"],
        json.dumps(snapshot, sort_keys=True)
    ))

def run():

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    settlement_metrics = collect_settlement_metrics(cur)
    reconciliation_metrics = collect_reconciliation_metrics(cur)
    router_metrics = collect_router_metrics(cur)
    external_truth_metrics = collect_external_truth_metrics(cur)

    metrics = {
        "settlement_metrics": settlement_metrics,
        "reconciliation_metrics": reconciliation_metrics,
        "router_metrics": router_metrics,
        "external_truth_metrics": external_truth_metrics
    }

    snapshot = build_health_snapshot(metrics)

    persist_snapshot(cur, snapshot)

    conn.commit()

    print("📡 OMEGA OPERATIONAL MONITORING v1")
    print(json.dumps(snapshot, indent=2))

    conn.close()

if __name__ == "__main__":
    run()

