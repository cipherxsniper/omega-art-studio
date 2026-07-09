import sqlite3
from pathlib import Path

token = "hs_bd_e26f7f2d56e94599"

for db_file in Path(".").glob("*.db"):
    try:
        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        
        for table in tables:
            try:
                cur.execute(f"PRAGMA table_info({table})")
                cols = [row[1] for row in cur.fetchall()]
                for col in cols:
                    cur.execute(f"SELECT * FROM {table} WHERE {col} LIKE ? LIMIT 3", (f"%{token}%",))
                    rows = cur.fetchall()
                    if rows:
                        print(f"✅ FOUND in {db_file} / {table} / {col}")
                        print(rows[0])
                        print("---")
            except:
                continue
        conn.close()
    except:
        continue
print("Search complete.")
