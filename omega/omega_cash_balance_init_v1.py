import sqlite3

def init_cash_balance(conn):
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cash_balance (
            id TEXT PRIMARY KEY,
            balance REAL DEFAULT 0
        )
    """)

    cur.execute("""
        INSERT OR IGNORE INTO cash_balance (id, balance)
        VALUES ('STRIPE_TREASURY', 0)
    """)

    conn.commit()
