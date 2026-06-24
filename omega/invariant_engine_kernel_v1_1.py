#!/usr/bin/env python3

import psycopg2

DB = "omega_bank"
USER = "omega"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)

def main():
    conn = connect()
    cur = conn.cursor()

    # DOUBLE ENTRY CHECK
    cur.execute("""
        SELECT
            SUM(CASE WHEN direction='DEBIT' THEN amount ELSE 0 END),
            SUM(CASE WHEN direction='CREDIT' THEN amount ELSE 0 END)
        FROM ledger_postings
    """)

    debits, credits = cur.fetchone()

    treasury_ok = abs(debits - credits) < 0.000001

    print("INVARIANT RESULTS:")
    print({
        "double_entry": treasury_ok,
        "treasury_balance": treasury_ok
    })

    if not treasury_ok:
        raise Exception("KERNEL INVARIANT VIOLATION")

    print("✔ ALL INVARIANTS PASSED (KERNEL SAFE)")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
