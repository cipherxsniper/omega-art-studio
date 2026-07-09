import sqlite3
from datetime import datetime

DB = "bank_links.db"

class BankLinkStore:

    def __init__(self):
        self.conn = sqlite3.connect(DB, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS bank_links (
            user_id TEXT PRIMARY KEY,
            bank_name TEXT,
            routing_number TEXT,
            account_number TEXT,
            nickname TEXT,
            created_at TEXT
        )
        """)
        self.conn.commit()

    def save(self, user_id, bank_name, routing, account, nickname):
        self.conn.execute("""
        INSERT OR REPLACE INTO bank_links
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            bank_name,
            routing,
            account,
            nickname,
            datetime.utcnow().isoformat()
        ))
        self.conn.commit()

    def get(self, user_id):
        cur = self.conn.execute(
            "SELECT * FROM bank_links WHERE user_id=?",
            (user_id,)
        )
        return cur.fetchone()
