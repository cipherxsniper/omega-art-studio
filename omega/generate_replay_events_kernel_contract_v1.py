#!/usr/bin/env python3

import psycopg2
import uuid
import json

DB = "omega_bank"
USER = "omega"

SYSTEM_WALLET = str(uuid.UUID("00000000-0000-0000-0000-000000000000"))
SYSTEM_MERCHANT = str(uuid.UUID("11111111-1111-1111-1111-111111111111"))

def connect():
    return psycopg2.connect(dbname=DB, user=USER)

def emit_event(cur, seq, event_type, aggregate_type, payload):

    event_id = str(uuid.uuid4())
    aggregate_id = str(uuid.uuid4())

    cur.execute("""
        INSERT INTO omega_events
        (event_id, event_type, aggregate_id, aggregate_type, payload, sequence_number)
        VALUES (%s, %s, %s, %s, %s::jsonb, %s)
    """, (
        event_id,
        event_type,
        aggregate_id,
        aggregate_type,
        json.dumps(payload),
        seq
    ))

def main():
    conn = connect()
    cur = conn.cursor()

    seq = 1

    # =========================
    # AUTH LIFECYCLE
    # =========================

    auth_id = str(uuid.uuid4())
    wallet_id = SYSTEM_WALLET

    emit_event(cur, seq, "AUTH_CREATED", "AUTH", {
        "wallet_id": wallet_id,
        "amount": 100.00,
        "currency": "USD"
    })
    seq += 1

    emit_event(cur, seq, "AUTH_CAPTURED", "AUTH", {
        "wallet_id": wallet_id,
        "amount": 100.00,
        "currency": "USD"
    })
    seq += 1

    emit_event(cur, seq, "AUTH_REVERSED", "AUTH", {
        "wallet_id": wallet_id,
        "amount": 100.00,
        "currency": "USD"
    })
    seq += 1

    emit_event(cur, seq, "AUTH_EXPIRED", "AUTH", {
        "wallet_id": wallet_id,
        "amount": 100.00,
        "currency": "USD"
    })
    seq += 1

    # =========================
    # PAYMENT LIFECYCLE
    # =========================

    emit_event(cur, seq, "PAYMENT_CAPTURED", "PAYMENT", {
        "merchant_id": SYSTEM_MERCHANT,
        "wallet_id": wallet_id,
        "amount": 100.00,
        "currency": "USD"
    })

    conn.commit()
    cur.close()
    conn.close()

    print("KERNEL CONTRACT EVENTS GENERATED (STRICT SCHEMA SAFE)")

if __name__ == "__main__":
    main()
