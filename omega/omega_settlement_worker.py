import psycopg2
import json
import time
from datetime import datetime

DB = "dbname=omega_bank user=omega"

def log(event, data):
    print(json.dumps({
        "ts": datetime.utcnow().isoformat(),
        "event": event,
        "data": data
    }))

def get_job(cur):
    cur.execute("""
        UPDATE settlement_queue
        SET status='PROCESSING',
            processing_at=now(),
            updated_at=now()
        WHERE id = (
            SELECT id
            FROM settlement_queue
            WHERE status='PENDING'
            ORDER BY created_at
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        RETURNING *;
    """)
    return cur.fetchone()

def apply_ledger(cur, job):
    payload = job[4]  # jsonb column

    amount = float(payload["amount"])
    from_wallet = payload["from_wallet"]
    to_wallet = payload["to_wallet"]

    idempotency_key = job[5]

    # DEBIT sender
    cur.execute("""
        INSERT INTO ledger_entries (
            id,
            transaction_id,
            wallet_id,
            direction,
            amount,
            idempotency_key,
            created_at
        )
        VALUES (
            gen_random_uuid(),
            %s,
            %s,
            'DEBIT',
            %s,
            %s,
            now()
        )
        ON CONFLICT (idempotency_key) DO NOTHING;
    """, (job[0], from_wallet, amount, idempotency_key + "-debit"))

    # CREDIT receiver
    cur.execute("""
        INSERT INTO ledger_entries (
            id,
            transaction_id,
            wallet_id,
            direction,
            amount,
            idempotency_key,
            created_at
        )
        VALUES (
            gen_random_uuid(),
            %s,
            %s,
            'CREDIT',
            %s,
            %s,
            now()
        )
        ON CONFLICT (idempotency_key) DO NOTHING;
    """, (job[0], to_wallet, amount, idempotency_key + "-credit"))

def finalize(cur, job_id):
    cur.execute("""
        UPDATE settlement_queue
        SET status='SETTLED',
            updated_at=now()
        WHERE id=%s;
    """, (job_id,))

def run():
    conn = psycopg2.connect(DB)
    conn.autocommit = False

    while True:
        try:
            with conn.cursor() as cur:

                job = get_job(cur)
                if not job:
                    time.sleep(1)
                    continue

                log("JOB_CLAIMED", {"id": str(job[0])})

                apply_ledger(cur, job)

                finalize(cur, job[0])

                conn.commit()

                log("JOB_SETTLED", {"id": str(job[0])})

        except Exception as e:
            conn.rollback()
            log("WORKER_ERROR", {"error": str(e)})
            time.sleep(1)

if __name__ == "__main__":
    run()
