#!/usr/bin/env python3

import json
import uuid
import psycopg2
from decimal import Decimal
from datetime import datetime, timedelta

DB_NAME = "omega_bank"
DB_USER = "omega"
DB_PASSWORD = ""
DB_HOST = "localhost"
DB_PORT = "5432"


def db():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )


def insert_event(cur, event_type, aggregate_id, aggregate_type, payload, seq):

    event_id = str(uuid.uuid4())
    idempotency_key = str(uuid.uuid4())

    cur.execute("""
        INSERT INTO omega_events (
            event_id,
            event_type,
            aggregate_id,
            aggregate_type,
            payload,
            idempotency_key,
            sequence_number,
            created_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, NOW()
        )
    """, (
        event_id,
        event_type,
        aggregate_id,
        aggregate_type,
        json.dumps(payload),
        idempotency_key,
        seq
    ))

    print(f"Inserted {event_type} seq={seq}")


def main():

    conn = db()

    try:

        wallet_id = str(uuid.uuid4())
        merchant_id = str(uuid.uuid4())
        auth_id = str(uuid.uuid4())

        seq = 1

        with conn.cursor() as cur:

            insert_event(
                cur,
                "AUTH_CREATED",
                auth_id,
                "AUTHORIZATION",
                {
                    "auth_id": auth_id,
                    "wallet_id": wallet_id,
                    "merchant_id": merchant_id,
                    "amount": "100.00",
                    "currency": "USD",
                    "expires_in_minutes": 15
                },
                seq
            )

            seq += 1

            insert_event(
                cur,
                "AUTH_CAPTURED",
                auth_id,
                "AUTHORIZATION",
                {
                    "auth_id": auth_id,
                    "wallet_id": wallet_id,
                    "merchant_id": merchant_id,
                    "captured_amount": "60.00"
                },
                seq
            )

            seq += 1

            insert_event(
                cur,
                "PAYMENT_CAPTURED",
                auth_id,
                "PAYMENT",
                {
                    "auth_id": auth_id,
                    "wallet_id": wallet_id,
                    "merchant_id": merchant_id,
                    "amount": "60.00"
                },
                seq
            )

            seq += 1

            insert_event(
                cur,
                "AUTH_REVERSED",
                auth_id,
                "AUTHORIZATION",
                {
                    "auth_id": auth_id,
                    "wallet_id": wallet_id,
                    "reason": "PARTIAL_REVERSAL"
                },
                seq
            )

            seq += 1

            insert_event(
                cur,
                "AUTH_EXPIRED",
                auth_id,
                "AUTHORIZATION",
                {
                    "auth_id": auth_id,
                    "wallet_id": wallet_id,
                    "reason": "HOLD_TIMEOUT"
                },
                seq
            )

        conn.commit()

        print("\nLEDGER EVENTS GENERATED SUCCESSFULLY")
        print(f"AUTH: {auth_id}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
