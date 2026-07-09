import sqlite3
import time
import uuid

DB = "leads.db"


class LeadsDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            company TEXT,
            source TEXT,
            score REAL DEFAULT 0,
            status TEXT DEFAULT 'new',
            created_at REAL
        )
        """)
        self.conn.commit()

    def add_lead(self, name, email, company, source):
        self.conn.execute("""
        INSERT INTO leads VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            name,
            email,
            company,
            source,
            0,
            "new",
            time.time()
        ))
        self.conn.commit()


leads_db = LeadsDB()
