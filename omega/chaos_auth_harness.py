#!/usr/bin/env python3

import time
import random
import uuid
import psycopg2

DB = {
    "dbname": "omega_bank",
    "user": "u0_a253",
    "password": "postgres",
    "host": "localhost",
    "port": 5432
}

def conn():
    return psycopg2.connect(**DB)


def create_auth_hold(cur, wallet_id, amount):
    auth_id = str(uuid.uuid4())

    cur.execute("""
        INSERT INTO authorization_holds
        (id, transaction_id, wallet_id, amount, status, merchant_name, currency, external_reference)
        VALUES
        (gen_random_uuid(), %s, %s, %s, 'AUTHORIZED', 'OMEGA_SANDBOX', 'USD', %s)
    """, (
        auth_id, wallet_id, amount, f"AUTH_{auth_id}"
    ))

    return auth_id


def simulate_capture(cur, auth_id, wallet_id, amount):

    # CHAOS: random delay + duplication simulation
    if random.random() < 0.2:
        time.sleep(random.uniform(0.1, 1.5))

    cur.execute("""
        UPDATE authorization_holds
        SET status='CAPTURED'
        WHERE transaction_id=%s
    """, (auth_id,))

    cur.execute("""
        INSERT INTO ledger_entries
        (id, transaction_id, wallet_id, direction, amount, idempotency_key)
        VALUES
        (gen_random_uuid(), %s, %s, 'DEBIT', %s, %s),
        (gen_random_uuid(), %s, %s, 'CREDIT', %s, %s)
    """, (
        auth_id, wallet_id, amount, f"debit-{auth_id}",
        auth_id, wallet_id, amount, f"credit-{auth_id}"
    ))


def run():
    conn = psycopg2.connect(**DB)

    wallets = [
        "8fcaf9c3-24d1-4c4b-ad88-856576b8b6e9",
        "7597e069-65bc-4b55-b420-a2a2682f53e0",
        "70e8cdae-983c-4392-a97a-4ae06217b303"
    ]

    while True:
        wallet = random.choice(wallets)
        amount = random.randint(10, 500)

        with conn:
            with conn.cursor() as cur:

                auth_id = create_auth_hold(cur, wallet, amount)

                # CHAOS: duplicate auth attempt simulation
                if random.random() < 0.3:
                    create_auth_hold(cur, wallet, amount)

                simulate_capture(cur, auth_id, wallet, amount)

        print(f"[CHAOS] AUTH->CAPTURE COMPLETE wallet={wallet} amount={amount}")
        time.sleep(0.5)


if __name__ == "__main__":
    run()
