#!/usr/bin/env python3

import time
import uuid
import psycopg2

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "password": "omega_pass",
    "host": "localhost"
}

def process_settlement_queue():

    conn = psycopg2.connect(**DB_CONFIG)

    while True:

        try:

            with conn:

                with conn.cursor() as cur:

                    cur.execute("""
                        SELECT
                            id,
                            auth_id,
                            wallet_id,
                            amount
                        FROM settlement_queue
                        WHERE status = 'PENDING'
                        ORDER BY created_at ASC
                        LIMIT 25
                        FOR UPDATE SKIP LOCKED
                    """)

                    rows = cur.fetchall()

                    for row in rows:

                        queue_id = row[0]
                        auth_id = row[1]
                        wallet_id = row[2]
                        amount = row[3]

                        settlement_id = str(uuid.uuid4())

                        cur.execute("""
                            INSERT INTO payment_settlements (
                                id,
                                auth_id,
                                wallet_id,
                                amount,
                                status
                            )
                            VALUES (%s,%s,%s,%s,'SETTLED')
                        """, (
                            settlement_id,
                            auth_id,
                            wallet_id,
                            amount
                        ))

                        cur.execute("""
                            UPDATE settlement_queue
                            SET status='SETTLED'
                            WHERE id=%s
                        """, (queue_id,))

                        print(
                            f"SETTLED :: "
                            f"{auth_id} :: "
                            f"{amount}"
                        )

            time.sleep(2)

        except Exception as e:

            print("SETTLEMENT WORKER ERROR")
            print(str(e))

            time.sleep(5)

if __name__ == "__main__":
    process_settlement_queue()
