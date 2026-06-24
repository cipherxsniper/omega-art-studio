#!/usr/bin/env python3

"""
=========================================================
OMEGA OPERATIONAL ENFORCEMENT ROUTER v1
Deterministic Financial Enforcement Decision Layer
NO DIRECT STATE MUTATION
GOVERNANCE CONTROLLED ACTION ROUTING
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
# FETCH LATEST DIVERGENCE STATE
# -----------------------------
def fetch_latest_divergence(cur):
    try:
        cur.execute("""
            SELECT event_hash, ledger_hash, divergence, decision, timestamp
            FROM omega_reconciliation_divergence_log
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        return cur.fetchone()
    except Exception:
        return None


# -----------------------------
# ENFORCEMENT DECISION ENGINE
# -----------------------------
def enforce(divergence_record):
    if not divergence_record:
        return {
            "action": "NO_OP",
            "freeze": 0,
            "recovery": 0,
            "fraud_flag": 0,
            "escalation": 0,
            "reason": "NO_DIVERGENCE_DATA"
        }

    event_hash, ledger_hash, divergence, decision, timestamp = divergence_record

    if not divergence:
        return {
            "action": "ALLOW_OPERATION",
            "freeze": 0,
            "recovery": 0,
            "fraud_flag": 0,
            "escalation": 0,
            "reason": "CONSENSUS_VALIDATED"
        }

    # Divergence detected → controlled enforcement routing
    return {
        "action": "ENFORCEMENT_TRIGGERED",
        "freeze": 1,
        "recovery": 1,
        "fraud_flag": 1,
        "escalation": 1,
        "reason": "TRUTH_DIVERGENCE_DETECTED"
    }


# -----------------------------
# MAIN EXECUTION
# -----------------------------
def run():
    conn = db()
    cur = conn.cursor()

    record = fetch_latest_divergence(cur)

    result = enforce(record)

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_present": record is not None,
        "decision": result,
        "deterministic_hash": hash_obj(result)
    }

    print("🧊 OMEGA OPERATIONAL ENFORCEMENT ROUTER v1")
    print(json.dumps(output, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
