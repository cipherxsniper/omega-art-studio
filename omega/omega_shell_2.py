#!/usr/bin/env python3

import sys
import sqlite3
from omega_db_registry import get_db

DB = get_db("ledger")
conn = sqlite3.connect(DB)

# ----------------------------
# LEDGER CORE
# ----------------------------

def get_balance():
    rows = conn.execute("""
        SELECT type, amount FROM ledger_events
    """).fetchall()

    balance = 0.0

    for r in rows:
        event_type = r[0]
        amount = r[1]

        if event_type in ("CREDIT", "INCOME"):
            balance += amount
        else:
            balance -= amount

    print(f"💰 BALANCE: {balance:.2f}")


def tail_ledger(n=10):
    rows = conn.execute("""
        SELECT id, type, amount, tx_id, timestamp
        FROM ledger_events
        ORDER BY timestamp DESC
        LIMIT ?
    """, (n,)).fetchall()

    for r in rows:
        print(r)


def list_accounts():
    try:
        rows = conn.execute("SELECT * FROM accounts").fetchall()
        for r in rows:
            print(r)
    except Exception as e:
        print("[WARN] accounts table missing:", e)


def stripe_sync():
    print("[OMEGA] Stripe sync placeholder (test mode only)")
    print("No live calls executed in this shell version.")


def simulate_tx(amount):
    conn.execute("""
        INSERT INTO ledger_events(type, counterparty, amount, tx_id, timestamp)
        VALUES ('SIMULATED', 'OMEGA_SHELL', ?, 'TX-SIM', strftime('%s','now'))
    """, (amount,))
    conn.commit()
    print(f"[OK] Simulated TX: {amount}")


# ----------------------------
# ROUTER
# ----------------------------

def main():
    if len(sys.argv) < 2:
        print("""
OMEGA FINANCIAL SHELL v1

Commands:
  balance
  ledger tail
  accounts
  stripe sync
  tx simulate <amount>
""")
        return

    cmd = sys.argv[1]

    if cmd == "balance":
        get_balance()

    elif cmd == "ledger":
        if len(sys.argv) > 2 and sys.argv[2] == "tail":
            tail_ledger()

    elif cmd == "accounts":
        list_accounts()

    elif cmd == "stripe":
        stripe_sync()

    elif cmd == "tx":
        if len(sys.argv) > 3 and sys.argv[2] == "simulate":
            simulate_tx(float(sys.argv[3]))

    else:
        print("Unknown command:", cmd)


if __name__ == "__main__":
    main()
