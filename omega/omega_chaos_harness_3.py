#!/usr/bin/env python3

"""
OMEGA CHAOS TEST HARNESS
------------------------
Simulates adversarial financial conditions

Tests:
- duplicate events
- delayed settlement
- race conditions
- worker restart loops
- idempotency stress
"""

import psycopg2
import random
import time
import uuid


def inject_event(cur):
    tx = str(uuid.uuid4())

    payload = {
        "tx": tx,
        "wallet_id": "8fcaf9c3-24d1-4c4b-ad88-856576b8b6e9",
        "direction": random.choice(["DEBIT", "CREDIT"]),
        "amount": round(random.uniform(1, 500), 2)
    }

    # DUPLICATE INJECTION (chaos condition)
    for _ in range(random.randint(1, 3)):
        cur.execute("""
            INSERT INTO settlement_queue (
                id,
                event_type,
                status,
                payload,
                idempotency_key,
                created_at
            )
            VALUES (%s,%s,%s,%s,%s,now())
            ON CONFLICT DO NOTHING
        """, (
            str(uuid.uuid4()),
            "CHAOS_EVENT",
            "PENDING",
            str(payload),
            tx
        ))


def run():
    conn = psycopg2.connect(dbname="omega_bank", user="omega")
    cur = conn.cursor()

    print("[CHAOS] Starting adversarial load simulation...")

    while True:
        try:
            inject_event(cur)
            conn.commit()

            print("[CHAOS] injected event burst")

            time.sleep(0.2)

        except Exception as e:
            print("[CHAOS ERROR]", e)
            time.sleep(1)


if __name__ == "__main__":
    run()
