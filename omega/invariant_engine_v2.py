#!/usr/bin/env python3

import psycopg2

DB = "omega_bank"
USER = "omega"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)

class InvariantEngine:

    def __init__(self):
        self.conn = connect()
        self.cur = self.conn.cursor()

    def check_double_entry(self):
        self.cur.execute("""
            SELECT
                SUM(CASE WHEN direction = 'debit' THEN amount ELSE 0 END),
                SUM(CASE WHEN direction = 'credit' THEN amount ELSE 0 END)
            FROM ledger_postings
        """)

        debits, credits = self.cur.fetchone()
        debits = debits or 0
        credits = credits or 0

        return abs(debits - credits) < 0.000001

    def check_treasury_balance(self):
        self.cur.execute("""
            SELECT account_type, SUM(amount)
            FROM ledger_postings
            GROUP BY account_type
        """)

        rows = self.cur.fetchall()

        wallet = 0
        merchant = 0
        treasury = 0

        for r in rows:
            atype, total = r
            total = total or 0

            if atype == "wallet":
                wallet = total
            elif atype == "merchant":
                merchant = total
            elif atype == "treasury":
                treasury = total

        return abs((wallet + merchant) - treasury) < 0.000001

    def run_all(self):
        results = {
            "double_entry": self.check_double_entry(),
            "treasury_balance": self.check_treasury_balance()
        }

        return results


if __name__ == "__main__":
    engine = InvariantEngine()
    result = engine.run_all()
    print("INVARIANT RESULTS:", result)

    if not all(result.values()):
        print("❌ INVARIANT FAILURE")
        exit(1)

    print("✅ ALL INVARIANTS PASSED")
