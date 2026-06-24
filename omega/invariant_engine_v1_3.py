import psycopg2
import json
import hashlib

class InvariantEngine:

    def __init__(self, conn):
        self.conn = conn

    def fetch_projections(self):
        cur = self.conn.cursor()

        cur.execute("""
            SELECT wallet_id, balance
            FROM wallet_balances
        """)
        wallets = cur.fetchall()

        cur.execute("""
            SELECT SUM(balance)
            FROM treasury_state
        """)
        treasury = cur.fetchone()[0] or 0

        return wallets, treasury

    def check_double_entry(self):
        cur = self.conn.cursor()

        cur.execute("""
            SELECT
                SUM((payload->>'debit')::numeric) as debits,
                SUM((payload->>'credit')::numeric) as credits
            FROM ledger_postings
        """)

        row = cur.fetchone()

        debits = row[0] or 0
        credits = row[1] or 0

        if debits != credits:
            self.log_failure("DOUBLE_ENTRY_VIOLATION", debits, credits)
            return False

        return True

    def check_treasury_balance(self):
        wallets, treasury = self.fetch_projections()

        wallet_sum = sum([w[1] for w in wallets])

        if wallet_sum != treasury:
            self.log_failure("TREASURY_DRIFT", wallet_sum, treasury)
            return False

        return True

    def check_authorization_integrity(self):
        cur = self.conn.cursor()

        cur.execute("""
            SELECT
                SUM(remaining_amount),
                SUM(reserved_amount)
            FROM authorization_state_projection
        """)

        row = cur.fetchone()

        if not row:
            return True

        remaining = row[0] or 0
        reserved = row[1] or 0

        if reserved < remaining:
            self.log_failure("AUTH_RESERVE_BREACH", reserved, remaining)
            return False

        return True

    def compute_state_hash(self):
        cur = self.conn.cursor()

        cur.execute("""
            SELECT event_id, event_type, payload
            FROM omega_events
            ORDER BY sequence_number ASC
        """)

        events = cur.fetchall()

        h = hashlib.sha256()

        for e in events:
            h.update(str(e).encode())

        return h.hexdigest()

    def run_all(self):
        results = {
            "double_entry": self.check_double_entry(),
            "treasury": self.check_treasury_balance(),
            "auth": self.check_authorization_integrity()
        }

        state_hash = self.compute_state_hash()

        return {
            "valid": all(results.values()),
            "checks": results,
            "state_hash": state_hash
        }

    def log_failure(self, code, a, b):
        cur = self.conn.cursor()

        cur.execute("""
            INSERT INTO invariant_failures(code, value_a, value_b)
            VALUES (%s, %s, %s)
        """, (code, str(a), str(b)))

        self.conn.commit()


def connect():
    return psycopg2.connect(
        dbname="omega_bank",
        user="omega",
        password="omega",
        host="localhost"
    )


if __name__ == "__main__":
    print("Activating invariant engine...")

    conn = connect()
    engine = InvariantEngine(conn)

    result = engine.run_all()

    print("\n===== INVARIANT CHECK RESULT =====")
    print(json.dumps(result, indent=2))

    if result["valid"]:
        print("\nINVARIANTS VALID ✓")
    else:
        print("\nINVARIANT VIOLATION DETECTED ⚠")
