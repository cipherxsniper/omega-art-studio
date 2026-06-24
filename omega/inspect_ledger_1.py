import sqlite3

DB = "omega_ledger.db"

def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    print("\n=== LEDGER ROW COUNT ===")
    cur.execute("SELECT COUNT(*) FROM ledger")
    print(cur.fetchone())

    print("\n=== LAST 20 TRANSACTIONS ===")
    cur.execute("SELECT * FROM ledger ORDER BY rowid DESC LIMIT 20")
    for row in cur.fetchall():
        print(row)

    print("\n=== BALANCE CHECK (if exists) ===")
    try:
        cur.execute("SELECT * FROM balances")
        print(cur.fetchall())
    except Exception as e:
        print("No balances table:", e)

    conn.close()

if __name__ == "__main__":
    run()
