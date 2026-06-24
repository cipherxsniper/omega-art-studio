#!/usr/bin/env python3

import sqlite3
import json

DB_PATH = "omega_ledger.db"


REQUIRED_COLUMNS = {
    "event_id": "TEXT",
    "event_type": "TEXT",
    "event_hash": "TEXT",
    "parent_hash": "TEXT",
    "payload_json": "TEXT",
    "created_at": "TEXT"
}


def get_columns(cur):
    cur.execute("PRAGMA table_info(ledger_events)")
    rows = cur.fetchall()

    cols = []

    for row in rows:
        cols.append(row[1])

    return cols


def ensure_ledger_table(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ledger_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT
    )
    """)


def patch_columns(cur, existing_cols):
    added = []

    for col, col_type in REQUIRED_COLUMNS.items():
        if col not in existing_cols:
            cur.execute(f"""
            ALTER TABLE ledger_events
            ADD COLUMN {col} {col_type}
            """)
            added.append(col)

    return added


def ensure_indexes(cur):
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_ledger_event_id
    ON ledger_events(event_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_ledger_event_hash
    ON ledger_events(event_hash)
    """)


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    ensure_ledger_table(cur)

    existing_cols = get_columns(cur)

    added = patch_columns(cur, existing_cols)

    ensure_indexes(cur)

    conn.commit()
    conn.close()

    print("🧠 LEDGER EVENTS SCHEMA PATCH v1")
    print(json.dumps({
        "existing_columns": existing_cols,
        "added_columns": added,
        "system_state": "LEDGER_SCHEMA_PATCHED"
    }, indent=2))


if __name__ == "__main__":
    run()
