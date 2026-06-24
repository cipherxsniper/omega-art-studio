import sqlite3
import time

DB = "omega_users.db"


class Subscriptions:
    def __init__(self):
        self.conn = sqlite3.connect(DB, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id TEXT PRIMARY KEY,
            plan TEXT,
            status TEXT,
            stripe_customer_id TEXT,
            updated_at REAL
        )
        """)
        self.conn.commit()

    def activate(self, user_id, plan, stripe_customer_id):
        self.conn.execute("""
        INSERT OR REPLACE INTO subscriptions
        (user_id, plan, status, stripe_customer_id, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, plan, "active", stripe_customer_id, time.time()))
        self.conn.commit()

    def deactivate(self, user_id):
        self.conn.execute("""
        UPDATE subscriptions
        SET status='inactive', updated_at=?
        WHERE user_id=?
        """, (time.time(), user_id))
        self.conn.commit()


subscriptions = Subscriptions()
