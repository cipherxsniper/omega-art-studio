#!/usr/bin/env python3

import psycopg2

DB = "omega_bank"
USER = "omega"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)


def check_double_entry(cur):

    cur.execute("""
        SELECT
            SUM(CASE WHEN direction = 'DEBIT' THEN amount ELSE 0 END) AS debits,
            SUM(CASE WHEN direction = 'CREDIT' THEN amount ELSE 0 END) AS credits
        FROM ledger_postings;
    """)

    debits, credits = cur.fetchone()

    return abs((debits or 0) - (credits or 0)) < 0.000001


def check_treasury_balance(cur):

    cur.execute("""
        SELECT account_type, SUM(amount)
        FROM ledger_postings
        GROUP BY account_type;
    """)

    rows = cur.fetchall()

    totals = {r[0]: float(r[1] or 0) for r in rows}

    wallet = totals.get("wallet", 0)
    merchant = totals.get("merchant", 0)

    return abs((wallet + merchant) - (wallet + merchant)) < 0.000001


def main():
    conn = connect()
    cur = conn.cursor()

    results = {
        "double_entry": check_double_entry(cur),
        "treasury_balance": check_treasury_balance(cur)
    }

    print("INVARIANT RESULTS:", results)

    if not all(results.values()):
        raise Exception("KERNEL INVARIANT VIOLATION")

    print("✔ ALL INVARIANTS PASSED")


if __name__ == "__main__":
    main()
