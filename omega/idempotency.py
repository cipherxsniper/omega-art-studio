import sqlite3

DB = "idempotency.db"

class IdempotencyStore:

    def __init__(self):
        self.conn = sqlite3.connect(DB, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY
        )
        """)
        self.conn.commit()

    def exists(self, key):
        cur = self.conn.execute("SELECT 1 FROM keys WHERE key=?", (key,))
        return cur.fetchone() is not None

    def mark(self, key):
        self.conn.execute("INSERT OR IGNORE INTO keys VALUES (?)", (key,))
        self.conn.commit()
