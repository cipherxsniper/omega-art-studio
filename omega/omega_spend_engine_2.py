#!/usr/bin/env python3

import uuid
import time
import hashlib
import psycopg2
from contextlib import contextmanager

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "password": "postgres",
    "host": "localhost",
    "port": 5432
}

OVERDRAFT_LIMIT = 0.00

SENDER_WALLET = "8fcaf9c3-24d1-4c4b-ad88-856576b8b6e9"
RECEIVER_WALLET = "7597e069-65bc-4b55-b420-a2a2682f53e0"

TRANSFER_AMOUNT = 250.00

@contextmanager
def db():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

def get_balance(wallet_id):

    with db() as conn:
        with conn.cursor() as cur:

            cur.execute("""

                SELECT COALESCE(
                    SUM(
                        CASE
                            WHEN direction='CREDIT'
                            THEN amount
                            ELSE -amount
                        END
                    ),
                    0
                )

                FROM ledger_entries
                WHERE wallet_id = %s

            """, (wallet_id,))

            row = cur.fetchone()

            return float(row[0] or 0)

def can_spend(wallet_id, amount):

    balance = get_balance(wallet_id)

    return (balance - amount) >= -OVERDRAFT_LIMIT

def atomic_transfer(sender, receiver, amount):

    tx_id = str(uuid.uuid4())

    debit_hash = hashlib.sha256(
        f"{tx_id}:{sender}:DEBIT:{amount}".encode()
    ).hexdigest()

    credit_hash = hashlib.sha256(
        f"{tx_id}:{receiver}:CREDIT:{amount}".encode()
    ).hexdigest()

    with db() as conn:

        with conn.cursor() as cur:

            cur.execute("""

                INSERT INTO ledger_entries
                (
                    id,
                    transaction_id,
                    wallet_id,
                    direction,
                    amount,
                    idempotency_key,
                    created_at
                )

                VALUES

                (
                    %s,
                    %s,
                    %s,
                    'DEBIT',
                    %s,
                    %s,
                    now()
                ),

                (
                    %s,
                    %s,
                    %s,
                    'CREDIT',
                    %s,
                    %s,
                    now()
                )

            """, (

                str(uuid.uuid4()),
                tx_id,
                sender,
                amount,
                debit_hash,

                str(uuid.uuid4()),
                tx_id,
                receiver,
                amount,
                credit_hash

            ))

        conn.commit()

    print("[SETTLED]", tx_id)

def worker():

    print("[OMEGA] Spend Engine Active")

    while True:

        try:

            if not can_spend(SENDER_WALLET, TRANSFER_AMOUNT):

                print("[FAILED] INSUFFICIENT FUNDS / OVERDRAFT LIMIT")

                time.sleep(5)

                continue

            atomic_transfer(
                SENDER_WALLET,
                RECEIVER_WALLET,
                TRANSFER_AMOUNT
            )

            sender_balance = get_balance(SENDER_WALLET)
            receiver_balance = get_balance(RECEIVER_WALLET)

            print()
            print("=== BALANCES ===")
            print("SENDER  :", sender_balance)
            print("RECEIVER:", receiver_balance)
            print()

            time.sleep(10)

        except Exception as e:

            print("[FAILED]", e)

            time.sleep(5)

if __name__ == "__main__":
    worker()

