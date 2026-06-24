#!/usr/bin/env python3
"""
OMEGA STRICT ACCOUNTING ENGINE v1
Single Source of Truth Balance Derivation
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "omega_ledger.db"


def compute_balances(cur):
    cur.execute("SELECT user_id, balance FROM accounts")
    rows = cur.fetchall()

    balances = {}
    total = 0.0

    for user_id, balance in rows:
        balances[user_id] = balance
        total += balance

    treasury = -total  # STRICT ACCOUNTING RULE

    return balances, treasury


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    balances, treasury = compute_balances(cur)

    print("🧠 STRICT ACCOUNTING OUTPUT")
    print({
        "balances": balances,
        "computed_treasury": treasury,
        "system_state": "STRICT_ACCOUNTING_ACTIVE"
    })

    conn.close()


if __name__ == "__main__":
    run()
