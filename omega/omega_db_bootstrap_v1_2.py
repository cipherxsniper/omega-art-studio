import sqlite3

def ensure_db():
    conn = sqlite3.connect("omega_ledger.db")
    cur = conn.cursor()

    # LEDGER TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ledger_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT,
            amount REAL,
            currency TEXT,
            created_at TEXT
        )
    """)

    # STRIPE TABLE (MISSING BEFORE — THIS CAUSED FAILURE)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stripe_events (
            event_id TEXT PRIMARY KEY,
            amount REAL,
            currency TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()

    return True


if __name__ == "__main__":
    print("🧱 DB BOOTSTRAP READY:", ensure_db())
