#!/usr/bin/env python3

import sqlite3

DB = "omega_ledger.db"

conn = sqlite3.connect(DB)

tables = conn.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
ORDER BY name
""").fetchall()

print("\n=== TABLES ===\n")

for t in tables:
    print(t[0])

print("\n=== SCHEMA DUMP ===\n")

for t in tables:

    table = t[0]

    print(f"\n--- {table} ---")

    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()

    for r in rows:
        print(r)

conn.close()
