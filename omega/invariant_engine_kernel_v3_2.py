#!/usr/bin/env python3

import psycopg2

DB = "omega_bank"
USER = "omega"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)


def check_double_entry_per_event(cur):

    cur.execute("""
        SELECT
            event_id,
            SUM(CASE WHEN direction = 'DEBIT' THEN amount ELSE 0 END) AS debits,
            SUM(CASE WHEN direction = 'CREDIT' THEN amount ELSE 0 END) AS credits
        FROM ledger_postings
        GROUP BY event_id;
    """)

    rows = cur.fetchall()

    for event_id, debits, credits in rows:
        if abs((debits or 0) - (credits or 0)) > 0.000001:
            print(f"VIOLATION EVENT: {event_id} D:{debits} C:{credits}")
            return False

    return True


def check_global_balance(cur):

    cur.execute("""
        SELECT
            SUM(CASE WHEN direction = 'DEBIT' THEN amount ELSE 0 END),
            SUM(CASE WHEN direction = 'CREDIT' THEN amount ELSE 0 END)
        FROM ledger_postings;
    """)

    debits, credits = cur.fetchone()

    return abs((debits or 0) - (credits or 0)) < 0.000001


def main():
    conn = connect()
    cur = conn.cursor()

    results = {
        "double_entry": check_double_entry_per_event(cur),
        "treasury_balance": check_global_balance(cur)
    }

    print("INVARIANT RESULTS:", results)

    if not all(results.values()):
        raise Exception("KERNEL INVARIANT VIOLATION")

    print("✔ ALL INVARIANTS PASSED")


if __name__ == "__main__":
    main()
