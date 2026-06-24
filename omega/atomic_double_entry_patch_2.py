import uuid
import psycopg2
from contextlib import contextmanager

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": 5432
}

@contextmanager
def db():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

def atomic_transfer(
    sender,
    receiver,
    amount,
    debit_hash,
    credit_hash
):
    tx_id = str(uuid.uuid4())

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
                    idempotency_key
                )

                VALUES

                (
                    %s,
                    %s,
                    %s,
                    'DEBIT',
                    %s,
                    %s
                ),

                (
                    %s,
                    %s,
                    %s,
                    'CREDIT',
                    %s,
                    %s
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

    print("[OMEGA] ATOMIC DOUBLE-ENTRY SUCCESS")
    print("TX:", tx_id)

if __name__ == "__main__":

    atomic_transfer(
        sender="8fcaf9c3-24d1-4c4b-ad88-856576b8b6e9",
        receiver="7597e069-65bc-4b55-b420-a2a2682f53e0",
        amount=250.00,
        debit_hash=uuid.uuid4().hex,
        credit_hash=uuid.uuid4().hex
    )
