import json
import psycopg2

def process_next_job(conn):
    with conn.cursor() as cur:

        # 1. CLAIM JOB (atomic lease)
        cur.execute("""
            UPDATE settlement_queue
            SET status='PROCESSING',
                processing_at = now(),
                updated_at = now()
            WHERE id = (
                SELECT id
                FROM settlement_queue
                WHERE status='PENDING'
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING id, payload, idempotency_key;
        """)

        job = cur.fetchone()
        if not job:
            return None

        job_id, payload, idem_key = job

        # 2. IDEMPOTENCY GUARD
        cur.execute("""
            SELECT 1 FROM ledger_entries
            WHERE idempotency_key = %s
        """, (idem_key,))

        if cur.fetchone():
            return

        # 3. SAFE PAYLOAD PARSE
        if isinstance(payload, str):
            data = json.loads(payload)
        else:
            data = payload

        # 4. EXECUTION (ledger append ONLY)
        cur.execute("""
            INSERT INTO ledger_entries (
                transaction_id,
                wallet_id,
                direction,
                amount,
                idempotency_key
            )
            VALUES (%s,%s,%s,%s,%s)
        """, (
            data["tx"],
            data["wallet_id"],
            data["direction"],
            data["amount"],
            idem_key
        ))

        # 5. MARK COMPLETE
        cur.execute("""
            UPDATE settlement_queue
            SET status='SETTLED',
                updated_at=now()
            WHERE id=%s
        """, (job_id,))

        conn.commit()


def run():
    conn = psycopg2.connect(
        dbname="omega_bank",
        user="omega",
        host="localhost"
    )

    while True:
        process_next_job(conn)


if __name__ == "__main__":
    run()
