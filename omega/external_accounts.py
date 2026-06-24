import sqlite3
from datetime import datetime

DB = "external_accounts.db"

class ExternalAccountStore:

    def __init__(self):
        self.conn = sqlite3.connect(DB, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS external_accounts (
            id TEXT,
            user_id TEXT,
            provider TEXT,
            label TEXT,
            identifier TEXT,
            created_at TEXT
        )
        """)
        self.conn.commit()

    def add_account(self, id, user_id, provider, label, identifier):
        self.conn.execute("""
        INSERT INTO external_accounts VALUES (?, ?, ?, ?, ?, ?)
        """, (
            id,
            user_id,
            provider,
            label,
            identifier,
            datetime.utcnow().isoformat()
        ))
        self.conn.commit()

    def get_accounts(self, user_id):
        return self.conn.execute(
            "SELECT * FROM external_accounts WHERE user_id=?",
            (user_id,)
        ).fetchall()
