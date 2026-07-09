#!/usr/bin/env python3
"""
OMEGA EVENT SOURCED LEDGER ENGINE
- entries = source of truth
- balances computed dynamically
- no state mutation in accounts table
"""

import sqlite3

DB = "omega_ledger.db"


def money(x):
    try:
        return float(x or 0)
    except:
        return 0.0


def compute_balances(conn):
    cur = conn.cursor()

    cur.execute("""
        SELECT account_id,
               SUM(CASE WHEN type='credit' THEN amount ELSE 0 END),
               SUM(CASE WHEN type='debit' THEN amount ELSE 0 END)
        FROM entries
        GROUP BY account_id
    """)

    rows = cur.fetchall()

    balances = {}

    for account_id, credits, debits in rows:
        balances[account_id] = money(credits) - money(debits)

    return balances


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    balances = compute_balances(conn)

    cur.execute("SELECT id, user_id FROM accounts")
    accounts = cur.fetchall()

    print("\n" + "═" * 80)
    print("🏦 OMEGA EVENT-SOURCED LEDGER VIEW")
    print("═" * 80)

    total = 0.0

    for acc_id, user in accounts:
        bal = balances.get(user, 0.0)
        total += bal

        print("\n┌──────────────────────────────────────────────┐")
        print(f"│ ACCOUNT : {user}")
        print(f"│ ID      : {acc_id}")
        print(f"│ BALANCE : ${bal:,.2f} USD")
        print("└──────────────────────────────────────────────┘")

    print("\n" + "═" * 80)
    print(f"💰 SYSTEM TOTAL (EVENT SOURCED): ${total:,.2f} USD")
    print("═" * 80)

    conn.close()


if __name__ == "__main__":
    main()
