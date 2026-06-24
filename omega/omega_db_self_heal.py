#!/usr/bin/env python3
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "omega_bank.db")

print("=== OMEGA DB SELF-HEAL ===")
print("DB PATH:", DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# CORE TABLES (idempotent safety)

cur.execute("""
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id TEXT,
    customer_id TEXT,
    status TEXT,
    price_id TEXT,
    created_at REAL,
    current_period_end REAL,
    cancel_at_period_end INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_id TEXT UNIQUE,
    source TEXT,
    status TEXT,
    amount REAL DEFAULT 0,
    created_at REAL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS stripe_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE,
    type TEXT,
    payload TEXT,
    created_at REAL
)
""")

conn.commit()
conn.close()

print("[OK] DB schema validated + repaired")
