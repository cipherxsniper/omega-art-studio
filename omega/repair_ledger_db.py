import sqlite3
import os

DB = "omega_ledger.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS ledger (
    id TEXT PRIMARY KEY,
    tx_type TEXT,
    amount REAL,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("[OK] ledger table ensured in omega_ledger.db")
