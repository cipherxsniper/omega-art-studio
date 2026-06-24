#!/usr/bin/env python3

import psycopg2

DB = "omega_bank"
USER = "omega"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)


def main():
    conn = connect()
    cur = conn.cursor()

    # GLOBAL BALANCE ONLY (multi-leg safe)
    cur.execute("""
        SELECT
            SUM(CASE WHEN direction = 'DEBIT' THEN amount ELSE 0 END),
            SUM(CASE WHEN direction = 'CREDIT' THEN amount ELSE 0 END)
        FROM ledger_postings;
    """)

    debits, credits = cur.fetchone()

    print("DEBITS:", debits)
    print("CREDITS:", credits)

    if abs((debits or 0) - (credits or 0)) > 0.000001:
        raise Exception("KERNEL INVARIANT VIOLATION")

    print("✔ GLOBAL BALANCE OK (MULTI-LEG MODE)")


if __name__ == "__main__":
    main()
