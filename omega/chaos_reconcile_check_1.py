#!/usr/bin/env python3

import psycopg2

DB = {
    "dbname": "omega_bank",
    "user": "u0_a253",
    "password": "postgres",
    "host": "localhost",
    "port": 5432
}

def run():
    conn = psycopg2.connect(**DB)

    with conn.cursor() as cur:

        # WALLET VS LEDGER DRIFT CHECK
        cur.execute("""
            SELECT w.id,
                   w.settled_balance,
                   COALESCE(SUM(
                       CASE WHEN le.direction='CREDIT' THEN le.amount
                       ELSE -le.amount END
                   ),0)
            FROM wallets w
            LEFT JOIN ledger_entries le ON w.id = le.wallet_id
            GROUP BY w.id, w.settled_balance
            HAVING w.settled_balance != COALESCE(SUM(
                CASE WHEN le.direction='CREDIT' THEN le.amount
                ELSE -le.amount END
            ),0)
        """)

        mismatches = cur.fetchall()

        print("\n[INVARIANT REPORT]")
        if not mismatches:
            print("OK - NO DRIFT DETECTED")
        else:
            for row in mismatches:
                print("DRIFT:", row)

if __name__ == "__main__":
    run()
