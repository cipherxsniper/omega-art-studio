#!/usr/bin/env python3

import sqlite3
import uuid

DB = "omega_ledger.db"

PURGE_USERS = [
    "SYSTEM",
    "REVENUE",
    "TOMMY",
    "TOMMY_LH"
]

conn = sqlite3.connect(DB)
cur = conn.cursor()

for user in PURGE_USERS:

    cur.execute("""
    SELECT id, balance
    FROM accounts
    WHERE user_id = ?
    """, (user,))

    row = cur.fetchone()

    if not row:
        continue

    acc_id, balance = row

    if float(balance) != 0:
        print(f"[SKIPPED NONZERO ACCOUNT] {user} => {balance}")
        continue

    cur.execute("""
    DELETE FROM accounts
    WHERE user_id = ?
    """, (user,))

    ledger_id = str(uuid.uuid4())

    cur.execute("""
    INSERT INTO ledger (
        id,
        tx_type,
        amount,
        status
    )
    VALUES (?, ?, ?, ?)
    """, (
        ledger_id,
        f"ACCOUNT_PURGED::{user}",
        0,
        "PURGED"
    ))

    print(f"[PURGED] {user}")

conn.commit()
conn.close()

print()
print("[OMEGA CLEANUP COMPLETE]")
