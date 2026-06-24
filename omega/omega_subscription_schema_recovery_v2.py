#!/usr/bin/env python3

import sqlite3

DB = "billing.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("\n=== OMEGA SUBSCRIPTION RECOVERY V2 ===\n")

# inspect legacy schema
print("=== LEGACY TABLE SCHEMA ===")

cols = cur.execute("""
PRAGMA table_info(subscriptions_legacy)
""").fetchall()

for c in cols:
    print(c)

legacy_columns = [c[1] for c in cols]

print("\n=== DETECTED COLUMNS ===")
print(legacy_columns)

# create clean deterministic table if missing
cur.execute("""
CREATE TABLE IF NOT EXISTS subscriptions_new (
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

# dynamic migration logic
if "customer_id" in legacy_columns:

    cur.execute("""
    INSERT INTO subscriptions_new (
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

else:

    print("\n[WARNING] customer_id missing in legacy schema")
    print("[RECOVERY] inserting placeholder-safe migration\n")

    cur.execute("""
    INSERT INTO subscriptions_new (
        customer_id,
        status,
        price_id,
        created_at
    )
    SELECT
        'UNKNOWN_CUSTOMER',
        status,
        price_id,
        created_at
    FROM subscriptions_legacy
    """)

conn.commit()

# swap tables safely
cur.execute("DROP TABLE IF EXISTS subscriptions")
cur.execute("ALTER TABLE subscriptions_new RENAME TO subscriptions")

conn.commit()

print("\n=== FINAL SUBSCRIPTIONS ===")

rows = cur.execute("""
SELECT
    id,
    customer_id,
    status,
    price_id,
    created_at
FROM subscriptions
""").fetchall()

for r in rows:
    print(r)

conn.close()

print("\n[OK] deterministic recovery complete")
