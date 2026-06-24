#!/usr/bin/env python3

"""
=========================================================
OMEGA SYSTEM OBSERVABILITY MESH v1
Unified Financial Infrastructure Telemetry Layer
Deterministic System-Wide Truth Streaming Engine
=========================================================
"""

import json
import hashlib
import sqlite3
from datetime import datetime, timezone

from omega_env_loader_v1 import get_db_path


# -----------------------------
# HASH ENGINE
# -----------------------------
def hash_obj(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True).encode()
    ).hexdigest()


# -----------------------------
# DB CONNECTION
# -----------------------------
def db():
    return sqlite3.connect(get_db_path())


# -----------------------------
# COLLECT SUBSYSTEM STATES
# -----------------------------
def collect_states(cur):
    state = {}

    tables = [
        ("governance", "governance_control_plane", "decision"),
        ("workers", "deterministic_worker_mesh", "coordination_state"),
        ("risk", "financial_risk_assessments", "risk_level"),
        ("replay", "external_webhook_replay_validation", "replay_status"),
        ("freeze", "operational_freeze_state", "freeze_state"),
        ("recovery", "operational_recovery_state", "current_state"),
    ]

    for key, table, column in tables:
        try:
            cur.execute(f"SELECT {column} FROM {table} ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            state[key] = row[0] if row else None
        except Exception:
            state[key] = None

    return state


# -----------------------------
# OBSERVABILITY ENGINE
# -----------------------------
def compute_observability(state):

    score = 1.0
    issues = []

    # governance visibility
    if not state.get("governance"):
        score -= 0.15
        issues.append("GOVERNANCE_MISSING")

    # worker health
    if state.get("workers") and "DEGRADED" in str(state["workers"]):
        score -= 0.2
        issues.append("WORKER_DEGRADATION")

    # risk presence
    if not state.get("risk"):
        score -= 0.1
        issues.append("RISK_SIGNAL_MISSING")

    # replay integrity
    if state.get("replay") and "DIVERGENCE" in str(state["replay"]):
        score -= 0.25
        issues.append("REPLAY_DIVERGENCE")

    # freeze system health
    if state.get("freeze") and "ACTIVE_LOCK" not in str(state["freeze"]):
        score -= 0.1
        issues.append("FREEZE_INACTIVE")

    # recovery system
    if not state.get("recovery"):
        score -= 0.1
        issues.append("RECOVERY_MISSING")

    return round(max(0.0, min(1.0, score)), 4), issues


# -----------------------------
# MAIN
# -----------------------------
def run():

    conn = db()
    cur = conn.cursor()

    state = collect_states(cur)
    score, issues = compute_observability(state)

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "observability_score": score,
        "issues_detected": issues,
        "subsystem_state": state,
        "deterministic_hash": hash_obj({
            "state": state,
            "score": score,
            "issues": issues
        })
    }

    print("🌐 OMEGA SYSTEM OBSERVABILITY MESH v1")
    print(json.dumps(output, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
