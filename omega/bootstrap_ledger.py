import sqlite3

DB = "omega_ledger.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("🧱 BOOTSTRAPPING OMEGA LEDGER CORE SCHEMA")

# CORE EVENT TABLE (canonical)
cur.execute("""
CREATE TABLE ledger_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    event_type TEXT NOT NULL,   -- DEBIT / CREDIT
    amount REAL NOT NULL,
    tx_id TEXT,
    timestamp REAL DEFAULT (strftime('%s','now'))
)
""")

# ACCOUNTS TABLE
cur.execute("""
CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY,
    balance REAL DEFAULT 0
)
""")

# FINALITY CHAIN (from your previous upgrade)
cur.execute("""
CREATE TABLE finalized_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER,
    hash TEXT,
    prev_hash TEXT,
    timestamp REAL
)
""")

conn.commit()
conn.close()

print("✅ OMEGA LEDGER READY (CLEAN STATE)")
