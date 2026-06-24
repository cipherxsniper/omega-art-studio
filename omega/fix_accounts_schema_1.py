import sqlite3

DB = "omega_ledger.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cols = [c[1] for c in cur.execute("PRAGMA table_info(accounts)")]

if "account_number" not in cols:
    cur.execute("ALTER TABLE accounts ADD COLUMN account_number TEXT")

if "routing_number" not in cols:
    cur.execute("ALTER TABLE accounts ADD COLUMN routing_number TEXT")

if "wallet_addr" not in cols:
    cur.execute("ALTER TABLE accounts ADD COLUMN wallet_addr TEXT")

conn.commit()
conn.close()

print("[SCHEMA FIX COMPLETE] accounts upgraded safely")
