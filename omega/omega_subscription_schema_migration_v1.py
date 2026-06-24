#!/usr/bin/env python3

import sqlite3

DB = "billing.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("\n=== OMEGA SUBSCRIPTION SCHEMA MIGRATION ===\n")

# backup old table
cur.execute("""
ALTER TABLE subscriptions
RENAME TO subscriptions_legacy
""")

# new deterministic schema
cur.execute("""
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id TEXT UNIQUE,
    customer_id TEXT,
    status TEXT,
    price_id TEXT,
    current_period_start REAL,
    current_period_end REAL,
    cancel_at_period_end INTEGER,
    created_at REAL
)
""")

# migrate old data safely
cur.execute("""
INSERT INTO subscriptions (
    customer_id,
    status,
    price_id,
    created_at
)
SELECT
    customer_id,
    status,
    price_id,
    created_at
FROM subscriptions_legacy
""")

conn.commit()

print("[OK] subscriptions schema upgraded")
print("[OK] legacy table preserved as subscriptions_legacy")

rows = cur.execute("""
SELECT
    id,
    customer_id,
    status,
    price_id
FROM subscriptions
""").fetchall()

print("\n=== CURRENT SUBSCRIPTIONS ===")
for r in rows:
    print(r)

conn.close()
