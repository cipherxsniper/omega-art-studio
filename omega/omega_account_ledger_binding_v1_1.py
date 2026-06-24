#!/usr/bin/env python3

import sqlite3
import psycopg2
import os
import json

SQLITE_DB = "omega_ledger.db"

PG_CONN = os.getenv("OMEGA_PG_CONN")


def load_accounts_pg():
    conn = psycopg2.connect(PG_CONN)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, owner_name
        FROM accounts
    """)

    rows = cur.fetchall()
    conn.close()

    return {r[0]: r[1] for r in rows}


def load_ledger_accounts(cur):
    cur.execute("SELECT DISTINCT json_extract(payload, '$.account_id') FROM ledger_events")
    rows = cur.fetchall()
    return set(r[0] for r in rows if r[0])


def bind_accounts(pg_accounts, ledger_accounts):
    bindings = []

    for acc_id, owner in pg_accounts.items():
        exists_in_ledger = acc_id in ledger_accounts

        bindings.append({
            "account_id": acc_id,
            "owner": owner,
            "ledger_linked": exists_in_ledger
        })

    return bindings


def run():
    print("🔗 OMEGA ACCOUNT LEDGER BINDING v1")

    pg_accounts = load_accounts_pg()

    conn = sqlite3.connect(SQLITE_DB)
    cur = conn.cursor()

    ledger_accounts = load_ledger_accounts(cur)

    bindings = bind_accounts(pg_accounts, ledger_accounts)

    print(json.dumps({
        "total_accounts": len(pg_accounts),
        "ledger_links": len([b for b in bindings if b["ledger_linked"]]),
        "unlinked": len([b for b in bindings if not b["ledger_linked"]]),
        "bindings": bindings
    }, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
