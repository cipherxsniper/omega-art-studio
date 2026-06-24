import sqlite3

conn = sqlite3.connect("omega_ledger.db")
cur = conn.cursor()

# Simple derived balance table (NO schema drift)
cur.execute("""
CREATE TABLE IF NOT EXISTS balances (
    id TEXT PRIMARY KEY DEFAULT 'global',
    total_credits REAL DEFAULT 0,
    total_debits REAL DEFAULT 0,
    net_balance REAL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# compute balances from ledger
cur.execute("""
SELECT 
    COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0),
    COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0)
FROM ledger
""")

credits, debits = cur.fetchone()
net = credits - debits

cur.execute("""
INSERT OR REPLACE INTO balances (id, total_credits, total_debits, net_balance, updated_at)
VALUES ('global', ?, ?, ?, CURRENT_TIMESTAMP)
""", (credits, debits, net))

conn.commit()
conn.close()

print("[OK] balances computed")
print("credits:", credits)
print("debits:", debits)
print("net:", net)
