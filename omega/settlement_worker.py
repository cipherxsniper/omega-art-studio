#!/usr/bin/env python3

import psycopg2
from invariant_engine import invariant_guard

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "u0_a253",
    "password": "postgres",
    "host": "localhost",
    "port": 5432
}

def db():
    return psycopg2.connect(**DB_CONFIG)


def run_worker():
    conn = db()

    while True:
        with conn:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT *
                    FROM settlement_queue
                    WHERE status='PENDING'
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                """)

                job = cur.fetchone()

                if not job:
                    continue

                job_id, event_type, status, payload, *_ = job

                cur.execute("""
                    UPDATE settlement_queue
                    SET status='PROCESSING',
                        processing_at=NOW()
                    WHERE id=%s
                """, (job_id,))

                conn.commit()

        with invariant_guard(conn):

            process(conn, job_id, payload)


def process(conn, job_id, payload):
    import json

    data = payload if isinstance(payload, dict) else json.loads(payload)

    from_wallet = data["from_wallet"]
    to_wallet = data["to_wallet"]
    amount = float(data["amount"])

    with conn.cursor() as cur:

        cur.execute("""
            INSERT INTO ledger_entries
            (id, transaction_id, wallet_id, direction, amount, idempotency_key)
            VALUES
            (gen_random_uuid(), %s, %s, 'DEBIT', %s, %s),
            (gen_random_uuid(), %s, %s, 'CREDIT', %s, %s)
        """, (
            job_id, from_wallet, amount, f"debit-{job_id}",
            job_id, to_wallet, amount, f"credit-{job_id}"
        ))

        cur.execute("""
            UPDATE wallets
            SET settled_balance = settled_balance - %s
            WHERE id=%s
        """, (amount, from_wallet))

        cur.execute("""
            UPDATE wallets
            SET settled_balance = settled_balance + %s
            WHERE id=%s
        """, (amount, to_wallet))

        cur.execute("""
            UPDATE settlement_queue
            SET status='SETTLED',
                updated_at=NOW()
            WHERE id=%s
        """, (job_id,))

        conn.commit()


if __name__ == "__main__":
    run_worker()
