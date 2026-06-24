#!/usr/bin/env python3

import sqlite3
import hashlib

DB = "omega_ledger.db"

conn = sqlite3.connect(DB)

rows = conn.execute("""
SELECT
    account_id,
    event_type,
    amount,
    tx_id
FROM ledger_events
ORDER BY id
""").fetchall()

h = hashlib.sha256()

for row in rows:
    h.update(str(row).encode())

print("\n=== DISTRIBUTED REPLAY VALIDATION ===")
print("EVENTS :", len(rows))
print("STATE HASH :", h.hexdigest())

conn.close()
