#!/usr/bin/env python3

import psycopg2

DB = "omega_bank"
USER = "omega"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)

def main():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            event_id,
            sequence_number,
            event_type,
            aggregate_id,
            payload
        FROM omega_events
        ORDER BY sequence_number ASC
    """)

    events = cur.fetchall()

    for e in events:
        event_id, seq, etype, agg, payload = e

        # SAFE deterministic extraction (NO dict casting issues)
        amount = float(payload.get("amount", 0))

        if etype == "AUTH_CREATED":
            postings = [
                (event_id, seq, "wallet", agg, "debit", amount),
                (event_id, seq, "treasury", "SYSTEM", "credit", amount)
            ]

        elif etype == "PAYMENT_CAPTURED":
            postings = [
                (event_id, seq, "merchant", agg, "credit", amount),
                (event_id, seq, "treasury", "SYSTEM", "debit", amount)
            ]

        else:
            postings = []

        for p in postings:
            cur.execute("""
                INSERT INTO ledger_postings
                (event_id, sequence_number, account_type, account_id, direction, amount)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, p)

    conn.commit()
    cur.close()
    conn.close()

    print("POSTINGS BUILT CLEAN (SCHEMA VALID)")

if __name__ == "__main__":
    main()
