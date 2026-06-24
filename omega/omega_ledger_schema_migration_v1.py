#!/usr/bin/env python3
"""
OMEGA LEDGER SCHEMA MIGRATION v1
Strict Accounting Mode Enforcement
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "omega_ledger.db"


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Ensure ledger_events exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ledger_events (
        id TEXT PRIMARY KEY,
        type TEXT,
        payload TEXT,
        timestamp TEXT
    )
    """)

    # SAFE MIGRATION: add missing column if needed
    try:
        cur.execute("ALTER TABLE ledger_events ADD COLUMN event_hash TEXT")
        print("✔ Added event_hash column")
    except sqlite3.OperationalError:
        print("✔ event_hash already exists (safe)")

    conn.commit()
    conn.close()

    print("🧠 SCHEMA MIGRATION COMPLETE (STRICT MODE READY)")


if __name__ == "__main__":
    run()
