import sqlite3
from pathlib import Path

db = Path.home() / "omega_ledger_2.db"
token = "hs_bd_e26f7f2d56e94599"

print("Searching for Genesis Black Diamond...")

conn = sqlite3.connect(str(db))
cur = conn.cursor()

tables = ["ledger_events", "entries", "ledger", "nft_registry", "events"]
for table in tables:
    try:
        cur.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in cur.fetchall()]
        for col in cols:
            cur.execute(f"SELECT * FROM {table} WHERE {col} LIKE ? LIMIT 3", (f"%{token}%",))
            rows = cur.fetchall()
            if rows:
                print(f"✅ FOUND in {table}.{col}")
                print(rows[0])
                print("---")
    except Exception as e:
        print(f"No {table} or error: {e}")

print("Search complete.")
conn.close()
