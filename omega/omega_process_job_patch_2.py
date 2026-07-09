import json

def process_job(conn, worker_id):
    with conn.cursor() as cur:

        # 1. CLAIM JOB (atomic lease)
        cur.execute("""
            SELECT id, payload, idempotency_key
            FROM settlement_queue
            WHERE status = 'PENDING'
            FOR UPDATE SKIP LOCKED
            LIMIT 1;
        """)

        job = cur.fetchone()
        if not job:
            return None

        job_id, payload, idem = job

        # 2. EXECUTION LOCK (idempotency gate)
        cur.execute("""
            SELECT 1 FROM execution_lease WHERE idempotency_key = %s;
        """, (idem,))
        if cur.fetchone():
            return None  # already executed

        cur.execute("""
            INSERT INTO execution_lease (idempotency_key, status, worker_id)
            VALUES (%s, 'LOCKED', %s)
            ON CONFLICT (idempotency_key) DO NOTHING;
        """, (idem, worker_id))

        # verify we own the lock
        cur.execute("""
            SELECT worker_id FROM execution_lease WHERE idempotency_key = %s;
        """, (idem,))
        owner = cur.fetchone()
        if not owner or owner[0] != worker_id:
            return None

        # 3. SAFE PAYLOAD PARSE (NO DICT CRASH)
        if isinstance(payload, str):
            data = json.loads(payload)
        else:
            data = payload

        # 4. LEDGER WRITE (IMMUTABLE ONLY)
        cur.execute("""
            INSERT INTO ledger_entries (
                transaction_id,
                wallet_id,
                direction,
                amount,
                idempotency_key
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (idempotency_key) DO NOTHING;
        """, (
            data["tx"],
            data["wallet_id"],
            data["direction"],
            data["amount"],
            idem
        ))

        # 5. MARK COMPLETE
        cur.execute("""
            UPDATE settlement_queue
            SET status = 'SETTLED',
                updated_at = now()
            WHERE id = %s;
        """, (job_id,))

        # 6. RELEASE LOCK (optional cleanup safety)
        cur.execute("""
            UPDATE execution_lease
            SET status = 'DONE'
            WHERE idempotency_key = %s;
        """, (idem,))

        conn.commit()
