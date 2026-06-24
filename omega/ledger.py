import sqlite3
import json

DB = "omega_ledger.db"

class LedgerEngine:
    def __init__(self):
        self.conn = sqlite3.connect(DB, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            type TEXT,
            payload TEXT,
            timestamp TEXT
        )
        """)
        self.conn.commit()

    def append(self, event):
        self.conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?)",
            (
                event["event_id"],
                event["event_type"],
                json.dumps(event["payload"]),
                event["timestamp"]
            )
        )
        self.conn.commit()

    def get_all(self):
        return self.conn.execute("SELECT * FROM events").fetchall()
