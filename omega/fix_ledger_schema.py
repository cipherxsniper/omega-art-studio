import sqlite3

DB = "omega_ledger.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("🔧 FIXING LEDGER SCHEMA...")

# Create canonical ledger_events table (event-sourced core)
cur.execute("""
CREATE TABLE IF NOT EXISTS ledger_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    amount REAL NOT NULL,
    timestamp REAL DEFAULT (strftime('%s','now'))
)
""")

# Optional safety index for chaos testing performance
cur.execute("""
CREATE INDEX IF NOT EXISTS idx_ledger_account
ON ledger_events(account_id)
""")

conn.commit()
conn.close()

print("✅ LEDGER SCHEMA READY")
