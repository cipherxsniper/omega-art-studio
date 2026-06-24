import sqlite3
import time

DB = "omega_ledger.db"


def post_event(account_id, event_type, amount):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO entries (account_id, type, amount, timestamp)
        VALUES (?, ?, ?, ?)
    """, (account_id, event_type, float(amount), time.time()))

    conn.commit()
    conn.close()
