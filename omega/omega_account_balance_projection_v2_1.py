#!/usr/bin/env python3

import sqlite3
import os

DB = os.path.expanduser("~/Omega-Production/omega_bank/omega_ledger.db")


def get_columns(cur, table):
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def compute_balances(cur):
    cols = get_columns(cur, "ledger_events")

    # SAFE column detection (no guessing)
    account_col = "account_id" if "account_id" in cols else None
    amount_col = "amount" if "amount" in cols else None

    if not account_col or not amount_col:
        raise Exception(f"Schema mismatch: ledger_events columns = {cols}")

    query = f"""
        SELECT {account_col}, SUM({amount_col})
        FROM ledger_events
        GROUP BY {account_col}
    """

    cur.execute(query)
    return cur.fetchall()


def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    print("📊 OMEGA BALANCE PROJECTION v2 (SCHEMA SAFE)")

    balances = compute_balances(cur)

    output = {
        "accounts": len(balances),
        "balances": balances
    }

    print(output)


if __name__ == "__main__":
    run()
