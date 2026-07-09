import sqlite3
import time

DB_PATH = "omega_ledger.db"


class EventProjectionEngine:
    """
    Live materialized ledger view.
    Listens to ledger_events and maintains accounts table in real-time.
    """

    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.cur = self.conn.cursor()
        self._ensure_tables()

    def _ensure_tables(self):
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_id TEXT PRIMARY KEY,
                balance REAL DEFAULT 0
            )
        """)
        self.conn.commit()

    def apply_event(self, account_id, event_type, amount):
        self.cur.execute("""
            INSERT OR IGNORE INTO accounts (account_id, balance)
            VALUES (?, 0)
        """, (account_id,))

        if event_type == "CREDIT":
            self.cur.execute("""
                UPDATE accounts
                SET balance = balance + ?
                WHERE account_id = ?
            """, (amount, account_id))

        elif event_type == "DEBIT":
            self.cur.execute("""
                UPDATE accounts
                SET balance = balance - ?
                WHERE account_id = ?
            """, (amount, account_id))

        self.conn.commit()

    def sync_all(self):
        """
        Full replay sync (safe recovery mode)
        """
        self.cur.execute("""
            SELECT account_id, event_type, amount
            FROM ledger_events
            ORDER BY rowid ASC
        """)

        for account_id, event_type, amount in self.cur.fetchall():
            self.apply_event(account_id, event_type, amount)

        print("🔄 LIVE PROJECTION SYNC COMPLETE")

    def watch(self, interval=2):
        """
        Poll-based live sync loop (production-lite event bus)
        """
        last_count = 0

        while True:
            self.cur.execute("SELECT COUNT(*) FROM ledger_events")
            count = self.cur.fetchone()[0]

            if count != last_count:
                self.sync_all()
                last_count = count

            time.sleep(interval)


if __name__ == "__main__":
    engine = EventProjectionEngine()
    engine.sync_all()
    engine.watch()
