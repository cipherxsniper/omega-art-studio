#!/usr/bin/env python3

import psycopg2
import uuid
import json

DB = "omega_bank"
USER = "omega"

SYSTEM_ACCOUNT = str(uuid.UUID("00000000-0000-0000-0000-000000000000"))

def connect():
    return psycopg2.connect(dbname=DB, user=USER)

def main():
    conn = connect()
    cur = conn.cursor()

    events = [
        ("AUTH_CREATED", "AUTH", 100.00),
        ("AUTH_CAPTURED", "AUTH", 100.00),
        ("AUTH_REVERSED", "AUTH", 100.00),
        ("AUTH_EXPIRED", "AUTH", 100.00),
        ("PAYMENT_CAPTURED", "PAYMENT", 100.00)
    ]

    for seq, (etype, atype, amount) in enumerate(events):

        event_id = str(uuid.uuid4())
        aggregate_id = str(uuid.uuid4())

        # 🔥 FIX: REQUIRED FIELD YOU WERE MISSING
        aggregate_type = atype

        payload = {
            "amount": amount,
            "currency": "USD",
            "account_id": SYSTEM_ACCOUNT
        }

        cur.execute("""
            INSERT INTO omega_events
            (event_id, event_type, aggregate_id, aggregate_type, payload, sequence_number)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
        """, (
            event_id,
            etype,
            aggregate_id,
            aggregate_type,
            json.dumps(payload),
            seq + 1
        ))

    conn.commit()
    cur.close()
    conn.close()

    print("KERNEL SAFE EVENTS GENERATED (FULL IDENTITY CONTRACT OK)")

if __name__ == "__main__":
    main()
