#!/usr/bin/env python3

import sqlite3
import json
from datetime import datetime, UTC

from omega_env_bootstrap_v1 import bootstrap_env

ENV = bootstrap_env()

DB_PATH = ENV.get(
    "OMEGA_DB_PATH",
    "/data/data/com.termux/files/home/Omega-Production/omega_bank/omega_ledger.db"
)

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_columns(cur):

    cur.execute("PRAGMA table_info(ledger_events)")
    rows = cur.fetchall()

    return [r["name"] for r in rows]

def ensure_canonical_columns(cur, columns):

    required = {
        "from_account": "TEXT",
        "to_account": "TEXT",
        "event_type": "TEXT",
        "amount": "REAL",
        "currency": "TEXT",
        "created_at": "TEXT"
    }

    for col, typ in required.items():

        if col not in columns:

            cur.execute(
                f"ALTER TABLE ledger_events ADD COLUMN {col} {typ}"
            )

def normalize_rows(cur, columns):

    cur.execute("SELECT * FROM ledger_events")
    rows = cur.fetchall()

    normalized = 0

    for row in rows:

        row_id = row["id"]

        updates = {}

        # from_account fallback
        if row["from_account"] is None:

            if "source" in columns and row["source"]:
                updates["from_account"] = row["source"]

            elif "account" in columns and row["account"]:
                updates["from_account"] = row["account"]

        # to_account fallback
        if row["to_account"] is None:

            if "destination" in columns and row["destination"]:
                updates["to_account"] = row["destination"]

            elif "counterparty" in columns and row["counterparty"]:
                updates["to_account"] = row["counterparty"]

        # event_type fallback
        if row["event_type"] is None:

            if "type" in columns and row["type"]:
                updates["event_type"] = row["type"]

            else:
                updates["event_type"] = "LEGACY_EVENT"

        # amount fallback
        if row["amount"] is None:

            if "value" in columns and row["value"]:
                updates["amount"] = row["value"]

        # currency fallback
        if row["currency"] is None:
            updates["currency"] = "USD"

        # timestamp fallback
        if row["created_at"] is None:

            if "timestamp" in columns and row["timestamp"]:
                updates["created_at"] = row["timestamp"]

            else:
                updates["created_at"] = datetime.now(UTC).isoformat()

        if updates:

            assignments = ", ".join([
                f"{k}=?"
                for k in updates.keys()
            ])

            values = list(updates.values())
            values.append(row_id)

            cur.execute(
                f"""
                UPDATE ledger_events
                SET {assignments}
                WHERE id=?
                """,
                values
            )

            normalized += 1

    return normalized

def create_replay_view(cur):

    cur.execute("""
    CREATE VIEW IF NOT EXISTS canonical_ledger_replay AS
    SELECT
        id,
        from_account,
        to_account,
        amount,
        currency,
        event_type,
        created_at
    FROM ledger_events
    WHERE
        from_account IS NOT NULL
        AND to_account IS NOT NULL
        AND amount IS NOT NULL
    """)

def run():

    conn = connect_db()
    cur = conn.cursor()

    columns = get_columns(cur)

    ensure_canonical_columns(cur, columns)

    columns = get_columns(cur)

    normalized = normalize_rows(cur, columns)

    create_replay_view(cur)

    conn.commit()
    conn.close()

    print("🧠 OMEGA CANONICAL LEDGER NORMALIZER v1")
    print(json.dumps({
        "normalized_rows": normalized,
        "canonical_view": "canonical_ledger_replay",
        "system_state": "CANONICAL_LEDGER_READY"
    }, indent=2))

if __name__ == "__main__":
    run()
