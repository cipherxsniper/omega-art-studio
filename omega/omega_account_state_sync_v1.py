#!/usr/bin/env python3

import sqlite3
from decimal import Decimal

LEDGER_DB = "omega_ledger.db"


def D(v):
    return Decimal(str(v))


def connect():
    return sqlite3.connect(LEDGER_DB)


def compute_balances(conn):

    rows = conn.execute("""
        SELECT
            account_id,
            event_type,
            amount
        FROM ledger_events
    """).fetchall()

    balances = {}

    for account_id, event_type, amount in rows:

        if account_id not in balances:
            balances[account_id] = Decimal("0")

        amount = D(amount)

        et = str(event_type).lower()

        if "credit" in et:
            balances[account_id] += amount

        elif "debit" in et:
            balances[account_id] -= amount

        else:
            balances[account_id] += amount

    return balances


def ensure_accounts_table(conn):

    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_id TEXT PRIMARY KEY,
            balance REAL
        )
    """)


def sync_accounts(conn, balances):

    cur = conn.cursor()

    for account_id, balance in balances.items():

        cur.execute("""
            INSERT OR REPLACE INTO accounts (
                account_id,
                balance
            ) VALUES (?, ?)
        """, (
            account_id,
            float(balance)
        ))

    conn.commit()


def main():

    conn = connect()

    ensure_accounts_table(conn)

    balances = compute_balances(conn)

    sync_accounts(conn, balances)

    print("\n=== ACCOUNT STATE SYNC COMPLETE ===\n")

    for k, v in balances.items():
        print(f"{k:<24} ${v:,.2f}")

    conn.close()


if __name__ == "__main__":
    main()
