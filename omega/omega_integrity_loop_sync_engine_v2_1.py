#!/usr/bin/env python3

"""
=========================================================
OMEGA INTEGRITY LOOP SYNC ENGINE v2
Bridge-Aware Deterministic Observability Layer
Reads normalized governance + freeze sync first
=========================================================
"""

import sqlite3
from datetime import datetime, timezone

from omega_env_loader_v1 import get_db_path


def db():
    return sqlite3.connect(get_db_path())


def safe_fetch(cur, query, fallback):
    try:
        cur.execute(query)
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else fallback
    except Exception:
        return fallback


def run():

    conn = db()
    cur = conn.cursor()

    now = datetime.now(timezone.utc).isoformat()

    # -----------------------------
    # PRIMARY SOURCE: BRIDGE TABLE
    # -----------------------------
    governance = safe_fetch(
        cur,
        "SELECT governance FROM governance_freeze_sync ORDER BY id DESC LIMIT 1",
        None
    )

    freeze = safe_fetch(
        cur,
        "SELECT freeze_state FROM governance_freeze_sync ORDER BY id DESC LIMIT 1",
        None
    )

    # -----------------------------
    # FALLBACK: LEGACY TABLES
    # -----------------------------
    if governance is None:
        governance = safe_fetch(
            cur,
            "SELECT decision FROM governance_control_plane ORDER BY id DESC LIMIT 1",
            "ALLOW_OPERATION"
        )

    if freeze is None:
        freeze = safe_fetch(
            cur,
            "SELECT freeze_state FROM operational_freeze_state ORDER BY id DESC LIMIT 1",
            "NO_FREEZE"
        )

    recovery = safe_fetch(
        cur,
        "SELECT current_state FROM operational_recovery_state ORDER BY id DESC LIMIT 1",
        "NO_RECOVERY"
    )

    # -----------------------------
    # SCORE CALCULATION
    # -----------------------------
    score = 1.0

    missing = []

    if governance is None:
        missing.append("GOVERNANCE_MISSING")
        score -= 0.3

    if freeze is None:
        missing.append("FREEZE_MISSING")
        score -= 0.3

    # -----------------------------
    # OUTPUT STATE
    # -----------------------------
    result = {
        "timestamp": now,
        "integrity_sync_score": round(max(score, 0.0), 2),
        "missing_feeds": missing,
        "system_sync_state": {
            "governance": governance,
            "recovery": recovery,
            "freeze": freeze
        }
    }

    print("🧠 OMEGA INTEGRITY LOOP SYNC ENGINE v2 (BRIDGE-AWARE)")
    print(result)

    conn.close()


if __name__ == "__main__":
    run()
