#!/usr/bin/env python3

import uuid
import random
import threading
import traceback
import time
import psycopg2

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "password": "omega_pass",

    # IMPORTANT:
    # Termux PostgreSQL socket path
    "host": "/data/data/com.termux/files/usr/tmp",

    "port": "5432",
    "connect_timeout": 10
}

WALLETS = [
    "fe881e17-8b24-42f4-ba4f-c1ce38770b51",
    "8fcaf9c3-24d1-4c4b-ad88-856576b8b6e9",
    "7597e069-65bc-4b55-b420-a2a2682f53e0",
    "70e8cdae-983c-4392-a97a-4ae06217b303"
]

MERCHANTS = [
    "OMEGA_STORE",
    "OMEGA_AI",
    "OMEGA_FOOD",
    "OMEGA_NETWORK",
    "OMEGA_CLOUD"
]

NETWORKS = [
    "VISA",
    "MASTERCARD"
]

def generate_transactions(worker_id):

    conn = None

    try:

        conn = psycopg2.connect(**DB_CONFIG)

        conn.autocommit = False

        print(f"[WORKER {worker_id}] CONNECTED")

        for i in range(250):

            auth_id = str(uuid.uuid4())

            wallet_id = random.choice(WALLETS)

            amount = round(random.uniform(5, 500), 2)

            merchant = random.choice(MERCHANTS)

            network = random.choice(NETWORKS)

            try:

                with conn.cursor() as cur:

                    cur.execute("""
                        INSERT INTO payment_authorizations (
                            id,
                            wallet_id,
                            merchant,
                            amount,
                            status,
                            network,
                            response_code,
                            created_at
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s,
                            'AUTHORIZED',
                            %s,
                            '00',
                            NOW()
                        )
                    """, (
                        auth_id,
                        wallet_id,
                        merchant,
                        amount,
                        network
                    ))

                    cur.execute("""
                        INSERT INTO settlement_queue (
                            auth_id,
                            wallet_id,
                            amount,
                            status,
                            created_at
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            'PENDING',
                            NOW()
                        )
                    """, (
                        auth_id,
                        wallet_id,
                        amount
                    ))

                conn.commit()

                print(
                    f"[WORKER {worker_id}] "
                    f"SUCCESS {amount}"
                )

            except Exception:

                conn.rollback()

                print(
                    f"[WORKER {worker_id}] "
                    f"TX FAILURE"
                )

                traceback.print_exc()

            time.sleep(0.01)

    except Exception:

        print(
            f"[WORKER {worker_id}] "
            f"CONNECTION FAILURE"
        )

        traceback.print_exc()

    finally:

        if conn:
            conn.close()

threads = []

for i in range(10):

    t = threading.Thread(
        target=generate_transactions,
        args=(i,)
    )

    t.start()

    threads.append(t)

for t in threads:
    t.join()

print("STRESS TEST COMPLETE")

