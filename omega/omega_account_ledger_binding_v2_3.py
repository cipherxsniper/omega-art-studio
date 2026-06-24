#!/usr/bin/env python3

import sqlite3
import os
import json

SQLITE_DB = "omega_ledger.db"


def load_accounts_pg_safe():
    """
    Safe PG loader:
    - does NOT crash system
    - allows offline ledger binding testing
    """
    pg_conn = os.getenv("OMEGA_PG_CONN")

    if not pg_conn:
        return None

    try:
        import psycopg2
        conn = psycopg2.connect(pg_conn)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, owner_name
            FROM accounts
        """)

        rows = cur.fetchall()
        conn.close()

        return {r[0]: r[1] for r in rows}

    except Exception as e:
        return {"error": str(e)}


def load_ledger_accounts(cur):
    cur.execute("""
        SELECT DISTINCT json_extract(payload, '$.account_id')
        FROM ledger_events
    """)

    rows = cur.fetchall()
    return set(r[0] for r in rows if r[0])


def load_sqlite_accounts(cur):
    cur.execute("SELECT id, user_id, balance FROM accounts")
    return cur.fetchall()


def run():
    print("🔗 OMEGA ACCOUNT LEDGER BINDING v2 (SAFE MODE)")

    conn = sqlite3.connect(SQLITE_DB)
    cur = conn.cursor()

    ledger_accounts = load_ledger_accounts(cur)
    sqlite_accounts = load_sqlite_accounts(cur)
    pg_accounts = load_accounts_pg_safe()

    report = {
        "sqlite_accounts": len(sqlite_accounts),
        "ledger_links": len(ledger_accounts),
        "pg_status": "DISCONNECTED" if pg_accounts is None else "CONNECTED",
        "pg_error": pg_accounts.get("error") if isinstance(pg_accounts, dict) else None,
        "ledger_bound_accounts": list(ledger_accounts)
    }

    print(json.dumps(report, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
