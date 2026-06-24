#!/usr/bin/env python3

"""
=========================================================
OMEGA RECONCILIATION DIVERGENCE ENGINE v1
Deterministic Financial Divergence Classification Layer
Replay-Safe Enforcement Trigger System
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
# FETCH LATEST REPLAY EVENTS
# -----------------------------
def fetch_latest_replay(cur):
    try:
        cur.execute("""
            SELECT event_hash, ledger_hash, divergence, decision, timestamp
            FROM omega_stripe_webhook_replay_logs
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        return cur.fetchone()
    except Exception:
        return None


# -----------------------------
# CLASSIFY DIVERGENCE
# -----------------------------
def classify(divergence: bool):
    if not divergence:
        return {
            "type": "NONE",
            "severity": "LOW",
            "freeze_recommendation": 0,
            "fraud_risk": 0.0
        }

    return {
        "type": "TRUTH_MISMATCH",
        "severity": "HIGH",
        "freeze_recommendation": 1,
        "fraud_risk": 0.72
    }


# -----------------------------
# ENGINE RUN
# -----------------------------
def run():
    conn = db()
    cur = conn.cursor()

    replay = fetch_latest_replay(cur)

    if not replay:
        print("🧠 OMEGA DIVERGENCE ENGINE v1")
        print("NO_REPLAY_DATA_AVAILABLE")
        return

    event_hash, ledger_hash, divergence, decision, timestamp = replay

    result = classify(bool(divergence))

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_hash": event_hash,
        "ledger_hash": ledger_hash,
        "divergence": bool(divergence),
        "decision": decision,
        "classification": result,
        "deterministic_hash": hash_obj({
            "event_hash": event_hash,
            "ledger_hash": ledger_hash,
            "decision": decision
        })
    }

    print("🧠 OMEGA RECONCILIATION DIVERGENCE ENGINE v1")
    print(json.dumps(output, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
