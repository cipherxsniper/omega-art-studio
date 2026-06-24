#!/usr/bin/env python3

import psycopg2
from decimal import Decimal

DB = "omega_bank"
USER = "omega"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)

def main():
    conn = connect()
    cur = conn.cursor()

    # FIXED: ALL EVENTS MUST HAVE FINANCIAL PAYLOADS

    events = [
        ("AUTH_CREATED", 100.00),
        ("AUTH_CAPTURED", 100.00),
        ("AUTH_REVERSED", 100.00),
        ("AUTH_EXPIRED", 100.00),
        ("PAYMENT_CAPTURED", 100.00)
    ]

    for i, (etype, amount) in enumerate(events):

        cur.execute("""
            INSERT INTO omega_events
            (event_id, sequence_number, event_type, payload)
            VALUES (uuid_generate_v4(), %s, %s, %s::jsonb)
        """, (
            i + 1,
            etype,
            f'{{"amount": {amount}, "currency": "USD", "account_id": "00000000-0000-0000-0000-000000000000"}}'
        ))

    conn.commit()
    cur.close()
    conn.close()

    print("KERNEL SAFE EVENT STREAM GENERATED")

if __name__ == "__main__":
    main()
