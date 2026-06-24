#!/usr/bin/env python3

import psycopg2
import uuid
import json
import sys

DB = {
    "dbname": "omega_bank",
    "user": "omega",
    "host": "localhost",
    "port": 5432
}

def hold(wallet_id, amount):
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    try:
        conn.autocommit = False

        event_id = str(uuid.uuid4())

        # 🔥 FIX: explicit UUID cast in SQL
        cur.execute("""
            SELECT reserve_funds(%s::uuid, %s::numeric)
        """, (wallet_id, amount))

        ok = cur.fetchone()[0]

        if not ok:
            conn.rollback()
            print("HOLD FAILED: INSUFFICIENT FUNDS")
            return

        payload = {
            "type": "HOLD",
            "wallet_id": wallet_id,
            "amount": float(amount)
        }

        cur.execute("""
            INSERT INTO settlement_queue (
                id,
                event_type,
                status,
                payload,
                idempotency_key,
                created_at,
                updated_at,
                retry_count,
                wallet_id,
                amount
            )
            VALUES (
                %s,
                'HOLD',
                'PENDING',
                %s,
                %s,
                NOW(),
                NOW(),
                0,
                %s,
                %s
            )
        """, (
            event_id,
            json.dumps(payload),
            event_id,
            wallet_id,
            amount
        ))

        conn.commit()
        print("HOLD SUCCESS:", event_id)

    except Exception as e:
        conn.rollback()
        print("HOLD FAILED:", e)

    finally:
        conn.close()

if __name__ == "__main__":
    hold(sys.argv[1], float(sys.argv[2]))
