#!/usr/bin/env python3

"""
=========================================================
OMEGA OPERATIONAL INTELLIGENCE INDEX v1
System-Wide Financial Infrastructure Truth Scoring Layer
Deterministic Institutional Integrity Engine
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
# COLLECT SYSTEM SIGNALS
# -----------------------------
def collect_signals(cur):
    signals = {}

    try:
        cur.execute("SELECT decision FROM governance_control_plane ORDER BY id DESC LIMIT 1")
        signals["governance"] = cur.fetchone()
    except Exception:
        signals["governance"] = None

    try:
        cur.execute("SELECT coordination_state FROM deterministic_worker_mesh ORDER BY id DESC LIMIT 1")
        signals["workers"] = cur.fetchone()
    except Exception:
        signals["workers"] = None

    try:
        cur.execute("SELECT risk_level, risk_score FROM financial_risk_assessments ORDER BY id DESC LIMIT 1")
        signals["risk"] = cur.fetchone()
    except Exception:
        signals["risk"] = None

    try:
        cur.execute("SELECT replay_status FROM external_webhook_replay_validation ORDER BY id DESC LIMIT 1")
        signals["replay"] = cur.fetchone()
    except Exception:
        signals["replay"] = None

    return signals


# -----------------------------
# SCORE ENGINE
# -----------------------------
def compute_index(signals):

    score = 1.0

    # governance penalty
    if signals["governance"] and "FREEZE" in str(signals["governance"]):
        score -= 0.3

    # worker instability
    if signals["workers"] and "DEGRADED" in str(signals["workers"]):
        score -= 0.2

    # risk penalty
    if signals["risk"]:
        try:
            risk_score = float(signals["risk"][1])
            score -= risk_score * 0.4
        except Exception:
            pass

    # replay divergence penalty
    if signals["replay"] and "DIVERGENCE" in str(signals["replay"]):
        score -= 0.25

    return max(0.0, min(1.0, round(score, 4)))


# -----------------------------
# MAIN
# -----------------------------
def run():
    conn = db()
    cur = conn.cursor()

    signals = collect_signals(cur)
    index = compute_index(signals)

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operational_intelligence_index": index,
        "signals": {
            "governance_present": signals["governance"] is not None,
            "worker_present": signals["workers"] is not None,
            "risk_present": signals["risk"] is not None,
            "replay_present": signals["replay"] is not None
        },
        "deterministic_hash": hash_obj({
            "index": index,
            "signals": str(signals)
        })
    }

    print("📊 OMEGA OPERATIONAL INTELLIGENCE INDEX v1")
    print(json.dumps(output, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
