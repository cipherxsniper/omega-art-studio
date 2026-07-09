#!/usr/bin/env python3

"""
=========================================================
OMEGA INTEGRITY LOOP SYNC ENGINE v1
Final Phase 5 Internal Consistency Closure Layer
Deterministic System-Wide Feed Synchronization Engine
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
# FETCH LATEST STATE
# -----------------------------
def fetch(cur, query):
    try:
        cur.execute(query)
        row = cur.fetchone()
        return row[0] if row else None
    except Exception:
        return None


# -----------------------------
# SYNC ENGINE
# -----------------------------
def sync_state(cur):

    return {
        "governance": fetch(cur, "SELECT decision FROM governance_control_plane ORDER BY id DESC LIMIT 1"),
        "recovery": fetch(cur, "SELECT current_state FROM operational_recovery_state ORDER BY id DESC LIMIT 1"),
        "freeze": fetch(cur, "SELECT freeze_state FROM operational_freeze_state ORDER BY id DESC LIMIT 1"),
        "worker": fetch(cur, "SELECT coordination_state FROM deterministic_worker_mesh ORDER BY id DESC LIMIT 1"),
        "risk": fetch(cur, "SELECT risk_level FROM financial_risk_assessments ORDER BY id DESC LIMIT 1"),
        "replay": fetch(cur, "SELECT replay_status FROM external_webhook_replay_validation ORDER BY id DESC LIMIT 1"),
    }


# -----------------------------
# CONSISTENCY SCORE
# -----------------------------
def compute_integrity(sync):

    score = 1.0

    missing = []

    for k, v in sync.items():
        if v is None:
            score -= 0.15
            missing.append(k.upper() + "_MISSING")

    # governance weighting
    if sync.get("governance") is None:
        score -= 0.1

    # recovery weighting
    if sync.get("recovery") is None:
        score -= 0.1

    return round(max(0.0, min(1.0, score)), 4), missing


# -----------------------------
# MAIN
# -----------------------------
def run():

    conn = db()
    cur = conn.cursor()

    sync = sync_state(cur)
    score, missing = compute_integrity(sync)

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "integrity_sync_score": score,
        "missing_feeds": missing,
        "system_sync_state": sync,
        "deterministic_hash": hash_obj({
            "sync": sync,
            "score": score
        })
    }

    print("🧠 OMEGA INTEGRITY LOOP SYNC ENGINE v1")
    print(json.dumps(output, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
