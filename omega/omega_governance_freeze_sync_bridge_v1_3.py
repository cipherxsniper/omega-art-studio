#!/usr/bin/env python3

"""
=========================================================
OMEGA GOVERNANCE + FREEZE SYNC BRIDGE v1
Deterministic Feed Normalization Layer
Closes final observability gaps for governance + freeze
=========================================================
"""

import sqlite3
from datetime import datetime, timezone

from omega_env_loader_v1 import get_db_path


# -----------------------------
# DB
# -----------------------------
def db():
    return sqlite3.connect(get_db_path())


# -----------------------------
# FETCH SAFE VALUE
# -----------------------------
def safe_fetch(cur, query, fallback):
    try:
        cur.execute(query)
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else fallback
    except Exception:
        return fallback


# -----------------------------
# MAIN
# -----------------------------
def run():

    conn = db()
    cur = conn.cursor()

    now = datetime.now(timezone.utc).isoformat()

    # GOVERNANCE NORMALIZATION
    governance = safe_fetch(
        cur,
        "SELECT decision FROM governance_control_plane ORDER BY id DESC LIMIT 1",
        "ALLOW_OPERATION"
    )

    governance_state = safe_fetch(
        cur,
        "SELECT governance_state FROM governance_control_plane ORDER BY id DESC LIMIT 1",
        "HEALTHY"
    )

    # FREEZE NORMALIZATION
    freeze = safe_fetch(
        cur,
        "SELECT freeze_state FROM operational_freeze_state ORDER BY id DESC LIMIT 1",
        "NO_FREEZE"
    )

    # WRITE NORMALIZED SNAPSHOT (OPTIONAL BUT IMPORTANT)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS governance_freeze_sync (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        governance TEXT,
        governance_state TEXT,
        freeze_state TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    INSERT INTO governance_freeze_sync (
        governance,
        governance_state,
        freeze_state,
        created_at
    ) VALUES (?, ?, ?, ?)
    """, (
        governance,
        governance_state,
        freeze,
        now
    ))

    conn.commit()

    print("🧠 OMEGA GOVERNANCE + FREEZE SYNC BRIDGE v1")
    print({
        "status": "SYNC_BRIDGE_COMPLETE",
        "governance": governance,
        "freeze": freeze,
        "timestamp": now
    })

    conn.close()


if __name__ == "__main__":
    run()
