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

def insert_event(cur, event_type, payload):
event_id = str(uuid.uuid4())

cur.execute("""
    INSERT INTO omega_events (
        event_id,
        event_type,
        payload,
        created_at
    )
    VALUES (%s, %s, %s, NOW())
""", (
    event_id,
    event_type,
    json.dumps(payload)
))

print(f"Inserted: {event_type}")
return event_id

def main():
conn = db()

try:
    wallet_id = str(uuid.uuid4())
    merchant_id = str(uuid.uuid4())
    auth_id = str(uuid.uuid4())

    amount = Decimal("100.00")
    expires_at = (datetime.utcnow() + timedelta(minutes=15)).isoformat()

    with conn.cursor() as cur:

        insert_event(cur, "AUTH_CREATED", {
            "auth_id": auth_id,
            "wallet_id": wallet_id,
            "merchant_id": merchant_id,
            "amount": str(amount),
            "currency": "USD",
            "expires_at": expires_at
        })

        insert_event(cur, "AUTH_CAPTURED", {
            "auth_id": auth_id,
            "wallet_id": wallet_id,
            "merchant_id": merchant_id,
            "amount": "60.00",
            "currency": "USD"
        })

        insert_event(cur, "PAYMENT_CAPTURED", {
            "auth_id": auth_id,
            "wallet_id": wallet_id,
            "merchant_id": merchant_id,
            "amount": "60.00",
            "currency": "USD"
        })

        insert_event(cur, "AUTH_REVERSED", {
            "auth_id": auth_id,
            "wallet_id": wallet_id,
            "merchant_id": merchant_id,
            "reason": "PARTIAL_REVERSAL"
        })

        insert_event(cur, "AUTH_EXPIRED", {
            "auth_id": auth_id,
            "wallet_id": wallet_id,
            "merchant_id": merchant_id,
            "reason": "HOLD_TIMEOUT"
        })

    conn.commit()

    print("\nREPLAY EVENTS GENERATED")
    print(wallet_id, merchant_id, auth_id)

finally:
    conn.close()

if name == "main":
main()
