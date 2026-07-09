#!/usr/bin/env python3

import sqlite3
from omega_db_registry import get_db

DB = get_db("ledger")
conn = sqlite3.connect(DB)

print("=== OMEGA FULL SYSTEM INTEGRITY TEST ===\n")

# -------------------------
# 1. SCHEMA CHECK
# -------------------------
print("[TEST 1] Schema inspection")

cols = conn.execute("PRAGMA table_info(ledger_events)").fetchall()
print("ledger_events columns:")
for c in cols:
    print(" ", c)

# -------------------------
# 2. EVENT COUNT CHECK
# -------------------------
print("\n[TEST 2] Event volume")

count = conn.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0]
print("Total events:", count)

# -------------------------
# 3. TX ID UNIQUENESS
# -------------------------
print("\n[TEST 3] TX uniqueness")

dupes = conn.execute("""
SELECT tx_id, COUNT(*)
FROM ledger_events
GROUP BY tx_id
HAVING COUNT(*) > 1
""").fetchall()

print("Duplicate tx_ids:", dupes)

# -------------------------
# 4. LEDGER BALANCE CHECK
# -------------------------
print("\n[TEST 4] Balance integrity")

rows = conn.execute("""
SELECT event_type, amount
FROM ledger_events
""").fetchall()

balance = 0

for r in rows:
    t = r[0]
    amt = r[1]

    if t in ("CREDIT", "INCOME"):
        balance += amt
    else:
        balance -= amt

print("Computed system balance:", balance)

# -------------------------
# 5. ORPHAN EVENT CHECK
# -------------------------
print("\n[TEST 5] Event structure sanity")

bad = conn.execute("""
SELECT *
FROM ledger_events
WHERE tx_id IS NULL OR amount IS NULL
""").fetchall()

print("Malformed events:", len(bad))

print("\n=== END OF TEST ===")
