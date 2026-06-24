#!/usr/bin/env python3
"""
OMEGA SETTLEMENT PIPELINE v2
Stateful financial lifecycle engine
"""

import sqlite3
import time

DB = "omega_ledger.db"


def init():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settlements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tx_id TEXT,
        from_acct TEXT,
        to_acct TEXT,
        amount REAL,
        state TEXT,
        timestamp REAL
    )
    """)

    conn.commit()
    conn.close()


def create_tx(tx_id, from_acct, to_acct, amount):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO settlements (tx_id, from_acct, to_acct, amount, state, timestamp)
        VALUES (?, ?, ?, ?, 'PENDING', ?)
    """, (tx_id, from_acct, to_acct, amount, time.time()))

    conn.commit()
    conn.close()


def advance_state(tx_id, new_state):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        UPDATE settlements
        SET state = ?
        WHERE tx_id = ?
    """, (new_state, tx_id))

    conn.commit()
    conn.close()


def lifecycle_demo():
    print("SETTLEMENT PIPELINE v2 ACTIVE")

    # Example lifecycle flow
    create_tx("TX-001", "THOMAS_LH", "TREASURY", 1000)

    advance_state("TX-001", "CLEARED")
    advance_state("TX-001", "SETTLED")
    advance_state("TX-001", "FINALIZED")

    print("SAMPLE TX COMPLETED")


if __name__ == "__main__":
    init()
    lifecycle_demo()
