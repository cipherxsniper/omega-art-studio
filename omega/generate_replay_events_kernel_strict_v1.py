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

def emit(cur, seq, event_type, aggregate_type, payload):

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
    # AUTH EVENTS (STRICT CONTRACT)
    # =========================

    def auth_event(event_type):
        return {
            "wallet_id": SYSTEM_WALLET,
            "amount": 100.00,
            "currency": "USD"
        }

    emit(cur, seq, "AUTH_CREATED", "AUTH", auth_event("AUTH_CREATED")); seq += 1
    emit(cur, seq, "AUTH_CAPTURED", "AUTH", auth_event("AUTH_CAPTURED")); seq += 1
    emit(cur, seq, "AUTH_REVERSED", "AUTH", auth_event("AUTH_REVERSED")); seq += 1
    emit(cur, seq, "AUTH_EXPIRED", "AUTH", auth_event("AUTH_EXPIRED")); seq += 1

    # =========================
    # PAYMENT EVENTS (STRICT CONTRACT)
    # =========================

    def payment_event():
        return {
            "merchant_id": SYSTEM_MERCHANT,
            "wallet_id": SYSTEM_WALLET,
            "amount": 100.00,
            "currency": "USD"
        }

    emit(cur, seq, "PAYMENT_CAPTURED", "PAYMENT", payment_event()); seq += 1

    conn.commit()
    cur.close()
    conn.close()

    print("KERNEL STRICT CONTRACT EVENTS GENERATED (NO PARTIAL PAYLOADS POSSIBLE)")

if __name__ == "__main__":
    main()
