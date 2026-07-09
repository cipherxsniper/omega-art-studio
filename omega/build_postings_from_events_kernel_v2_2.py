#!/usr/bin/env python3

import psycopg2
from financial_kernel_validator_v1 import validate_event

DB = "omega_bank"
USER = "omega"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)

def main():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT event_id, sequence_number, event_type, payload, created_at
        FROM omega_events
        ORDER BY sequence_number ASC
    """)

    events = cur.fetchall()

    for e in events:
        event_id, seq, event_type, payload, created_at = e

        ok, reason = validate_event(event_type, event_id, payload)

        if not ok:
            print(f"KERNEL REJECTED EVENT: {event_type} {event_id} -> {reason}")
            continue

        account_id = payload.get("account_id")
        amount = float(payload.get("amount", 0))
        currency = payload.get("currency", "USD")

        direction = "DEBIT" if event_type in ["AUTH_CAPTURED", "PAYMENT_CAPTURED"] else "CREDIT"

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
            amount,
            currency
        ))

    conn.commit()
    cur.close()
    conn.close()

    print("KERNEL POSTINGS COMPLETE (STRICT CONTRACT MODE)")

if __name__ == "__main__":
    main()
