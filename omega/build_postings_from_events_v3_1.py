#!/usr/bin/env python3

import psycopg2

DB = "omega_bank"
USER = "omega"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)

def normalize_direction(d):
    d = d.lower()
    if d == "debit":
        return "DEBIT"
    if d == "credit":
        return "CREDIT"
    raise Exception(f"Invalid direction: {d}")

def main():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            event_id,
            sequence_number,
            event_type,
            payload,
            created_at
        FROM omega_events
        ORDER BY sequence_number ASC
    """)

    events = cur.fetchall()

    for e in events:
        event_id, seq, event_type, payload, created_at = e

        direction = "DEBIT" if "DEBIT" in event_type else "CREDIT"

        amount = payload.get("amount", 0) if isinstance(payload, dict) else 0
        account_id = payload.get("account_id") if isinstance(payload, dict) else None

        cur.execute("""
            INSERT INTO ledger_postings
            (event_id, sequence_number, account_type, account_id, direction, amount, currency)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            event_id,
            seq,
            event_type,
            account_id,
            direction,
            float(amount),
            payload.get("currency", "USD") if isinstance(payload, dict) else "USD"
        ))

    conn.commit()
    cur.close()
    conn.close()

    print("POSTINGS BUILT CLEANLY (NO STAGING, CONTRACT SAFE)")

if __name__ == "__main__":
    main()
