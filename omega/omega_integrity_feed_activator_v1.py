#!/usr/bin/env python3

"""
=========================================================
OMEGA INTEGRITY FEED ACTIVATOR v1 (SAFE SCHEMA VERSION)
Deterministic Bootstrap + Schema Migration Layer
Banking-grade safe table evolution system
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
# TABLE CHECK
# -----------------------------
def table_columns(cur, table):
    try:
        cur.execute(f"PRAGMA table_info({table})")
        return [row[1] for row in cur.fetchall()]
    except Exception:
        return []


# -----------------------------
# SAFE MIGRATION
# -----------------------------
def ensure_schema(cur):

    # GOVERNANCE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS governance_control_plane (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision TEXT,
        severity TEXT,
        governance_state TEXT,
        created_at TEXT
    )
    """)

    # RECOVERY
    cur.execute("""
    CREATE TABLE IF NOT EXISTS operational_recovery_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        current_state TEXT,
        created_at TEXT
    )
    """)

    # FREEZE (FIXED SAFE SCHEMA)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS operational_freeze_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        freeze_state TEXT,
        created_at TEXT
    )
    """)


# -----------------------------
# SAFE BOOTSTRAP INSERT
# -----------------------------
def safe_insert(cur, table, cols, values):

    existing_cols = table_columns(cur, table)

    filtered_cols = []
    filtered_vals = []

    for c, v in zip(cols, values):
        if c in existing_cols:
            filtered_cols.append(c)
            filtered_vals.append(v)

    placeholders = ",".join(["?"] * len(filtered_vals))

    col_sql = ",".join(filtered_cols)

    cur.execute(
        f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})",
        filtered_vals
    )


# -----------------------------
# MAIN
# -----------------------------
def run():

    conn = db()
    cur = conn.cursor()

    ensure_schema(cur)

    now = datetime.now(timezone.utc).isoformat()

    # GOVERNANCE BOOTSTRAP
    cur.execute("SELECT COUNT(*) FROM governance_control_plane")
    if cur.fetchone()[0] == 0:
        safe_insert(
            cur,
            "governance_control_plane",
            ["decision", "severity", "governance_state", "created_at"],
            ["ALLOW_OPERATION", "LOW", "HEALTHY", now]
        )

    # RECOVERY BOOTSTRAP
    cur.execute("SELECT COUNT(*) FROM operational_recovery_state")
    if cur.fetchone()[0] == 0:
        safe_insert(
            cur,
            "operational_recovery_state",
            ["current_state", "created_at"],
            ["NO_RECOVERY", now]
        )

    # FREEZE BOOTSTRAP
    cur.execute("SELECT COUNT(*) FROM operational_freeze_state")
    if cur.fetchone()[0] == 0:
        safe_insert(
            cur,
            "operational_freeze_state",
            ["freeze_state", "created_at"],
            ["NO_FREEZE", now]
        )

    conn.commit()

    print("🔌 OMEGA INTEGRITY FEED ACTIVATOR v1 (SAFE)")
    print({
        "status": "SCHEMA_SAFE_BOOTSTRAP_COMPLETE",
        "timestamp": now
    })

    conn.close()


if __name__ == "__main__":
    run()
