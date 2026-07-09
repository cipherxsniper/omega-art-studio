import sqlite3
import time
import uuid

DB_PATH = "omega_ledger.db"


class Ledger:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init()

    def _init(self):
        c = self.conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            balance REAL DEFAULT 0
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id TEXT PRIMARY KEY,
            tx_id TEXT,
            account_id TEXT,
            type TEXT,
            amount REAL,
            created_at REAL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            tx_id TEXT PRIMARY KEY,
            source TEXT,
            status TEXT,
            created_at REAL
        )
        """)

        self.conn.commit()

    def create_account(self, user_id):
        acc_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO accounts (id, user_id, balance) VALUES (?, ?, ?)",
            (acc_id, user_id, 0.0)
        )
        self.conn.commit()
        return acc_id

    def post_transaction(self, tx_id, debit_acc, credit_acc, amount, source="stripe"):
        now = time.time()

        cur = self.conn.cursor()

        cur.execute("SELECT tx_id FROM transactions WHERE tx_id=?", (tx_id,))
        if cur.fetchone():
            return False

        cur.execute(
            "INSERT INTO transactions VALUES (?, ?, ?, ?)",
            (tx_id, source, "posted", now)
        )

        cur.execute(
            "INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), tx_id, debit_acc, "debit", amount, now)
        )

        cur.execute(
            "INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), tx_id, credit_acc, "credit", amount, now)
        )

        cur.execute("UPDATE accounts SET balance = balance - ? WHERE id=?", (amount, debit_acc))
        cur.execute("UPDATE accounts SET balance = balance + ? WHERE id=?", (amount, credit_acc))

        self.conn.commit()
        return True


ledger = Ledger()
