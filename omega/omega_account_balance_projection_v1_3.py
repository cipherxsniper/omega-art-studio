#!/usr/bin/env python3
"""
OMEGA ACCOUNT BALANCE PROJECTION v1
Deterministic ledger-derived balance engine (NO SOURCE OF TRUTH WRITES)

RULE:
- balances are derived ONLY from ledger_events
- accounts table is identity only
- Stripe is external truth, NOT balance authority
"""

import sqlite3
from datetime import datetime, timezone

DB = "/data/data/com.termux/files/home/Omega-Production/omega_bank/omega_ledger.db"


def get_conn():
    return sqlite3.connect(DB)


def compute_balances(cur):
    """
    Deterministic balance projection from ledger_events
    """
    cur.execute("""
        SELECT account_id, SUM(amount) as balance
        FROM ledger_events
        GROUP BY account_id
    """)
    rows = cur.fetchall()

    return [
        {
            "account_id": r[0],
            "balance": float(r[1] or 0.0)
        }
        for r in rows
    ]


def store_projection(cur, balances):
    """
    Store derived snapshot (append-only)
    """
    cur.execute("""
        CREATE TABLE IF NOT EXISTS account_balance_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT,
            balance REAL,
            created_at TEXT
        )
    """)

    now = datetime.now(timezone.utc).isoformat()

    for b in balances:
        cur.execute("""
            INSERT INTO account_balance_snapshots
            (account_id, balance, created_at)
            VALUES (?, ?, ?)
        """, (b["account_id"], b["balance"], now))


def run():
    conn = get_conn()
    cur = conn.cursor()

    balances = compute_balances(cur)
    store_projection(cur, balances)

    conn.commit()
    conn.close()

    print("🧠 OMEGA BALANCE PROJECTION COMPLETE")
    print({
        "accounts_projected": len(balances),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


if __name__ == "__main__":
    run()
