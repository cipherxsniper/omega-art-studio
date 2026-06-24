import sqlite3

DB = "omega_idempotency.db"


class Idempotency:
    def __init__(self):
        self.conn = sqlite3.connect(DB, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_events (
            event_id TEXT PRIMARY KEY
        )
        """)
        self.conn.commit()

    def seen(self, event_id):
        cur = self.conn.cursor()
        cur.execute("SELECT event_id FROM processed_events WHERE event_id=?", (event_id,))
        return cur.fetchone() is not None

    def mark(self, event_id):
        self.conn.execute(
            "INSERT INTO processed_events VALUES (?)",
            (event_id,)
        )
        self.conn.commit()


idempotency = Idempotency()
