#!/usr/bin/env python3

import psycopg2
import json
from contextlib import contextmanager

DB = {
    "dbname": "omega_bank",
    "user": "u0_a253",
    "password": "postgres",
    "host": "localhost",
    "port": 5432
}

@contextmanager
def db():
    conn = psycopg2.connect(**DB)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_next_job(cur):
    cur.execute("""
        SELECT id, payload
        FROM settlement_queue
        WHERE status = 'PENDING'
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    """)
    return cur.fetchone()


def lock_job(cur, job_id):
    cur.execute("""
        UPDATE settlement_queue
        SET status='PROCESSING',
            processing_at=NOW(),
            retry_count = retry_count + 1
        WHERE id=%s
    """, (job_id,))


def fetch_wallet(cur, wallet_id):
    cur.execute("""
        SELECT id, settled_balance, locked_balance
        FROM wallets
        WHERE id=%s
        FOR UPDATE
    """, (wallet_id,))
    return cur.fetchone()


def enforce_invariant(wallet, amount):
    available = float(wallet[1]) - float(wallet[2])
    if amount > available:
        raise Exception(f"[INVARIANT BLOCK] insufficient funds {amount} > {available}")


def write_ledger(cur, tx_id, wallet_id, direction, amount, key):
    cur.execute("""
        INSERT INTO ledger_entries
        (transaction_id, wallet_id, direction, amount, idempotency_key, created_at)
        VALUES (%s,%s,%s,%s,%s,NOW())
    """, (tx_id, wallet_id, direction, amount, key))


def process_job(cur, job):
    job_id, payload = job

    # FIX: jsonb already decoded by psycopg2
    data = payload if isinstance(payload, dict) else json.loads(payload)

    from_wallet = data["from_wallet"]
    to_wallet = data["to_wallet"]
    amount = float(data["amount"])

    lock_job(cur, job_id)

    w_from = fetch_wallet(cur, from_wallet)
    w_to = fetch_wallet(cur, to_wallet)

    enforce_invariant(w_from, amount)

    write_ledger(cur, job_id, from_wallet, "DEBIT", amount, f"debit-{job_id}")
    write_ledger(cur, job_id, to_wallet, "CREDIT", amount, f"credit-{job_id}")

    cur.execute("""
        UPDATE settlement_queue
        SET status='SETTLED',
            updated_at=NOW()
        WHERE id=%s
    """, (job_id,))


def main():
    print("[OMEGA] EXECUTION PIPELINE ONLINE")

    while True:
        with db() as conn:
            cur = conn.cursor()

            job = get_next_job(cur)
            if not job:
                continue

            try:
                process_job(cur, job)
                print("[SETTLED]", job[0])

            except Exception as e:
                cur.execute("""
                    UPDATE settlement_queue
                    SET status='FAILED'
                    WHERE id=%s
                """, (job[0],))

                cur.execute("""
                    INSERT INTO invariant_failures
                    (invariant_name, failure_details, severity)
                    VALUES ('EXECUTION_FAILURE', %s, 'CRITICAL')
                """, (str(e),))

                print("[FAILED]", e)


if __name__ == "__main__":
    main()
