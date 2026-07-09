import sqlite3
import uuid

DB = "omega_users.db"

class UserStore:
    def __init__(self):
        self.conn = sqlite3.connect(DB, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id TEXT PRIMARY KEY,
            user_uuid TEXT,
            name TEXT,
            pin TEXT,
            wallet_id TEXT
        )
        """)
        self.conn.commit()

    def get(self, telegram_id):
        cur = self.conn.execute(
            "SELECT * FROM users WHERE telegram_id=?",
            (str(telegram_id),)
        )
        return cur.fetchone()

    def create(self, telegram_id, name, pin):
        user_uuid = str(uuid.uuid4())
        wallet_id = str(uuid.uuid4())

        self.conn.execute("""
        INSERT INTO users VALUES (?, ?, ?, ?, ?)
        """, (
            str(telegram_id),
            user_uuid,
            name,
            pin,
            wallet_id
        ))

        self.conn.commit()

        return {
            "user_uuid": user_uuid,
            "wallet_id": wallet_id
        }

    def verify_pin(self, telegram_id, pin):
        user = self.get(telegram_id)
        if not user:
            return False
        return user[3] == pin
