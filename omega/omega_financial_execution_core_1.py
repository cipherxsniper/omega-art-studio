
import time
import uuid
import psycopg2

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "password": "postgres",
    "host": "localhost",
    "port": 5432
}

# =========================================================
# DB CONNECTION
# =========================================================

def db():
    return psycopg2.connect(**DB_CONFIG)

# =========================================================
# EVENT BUS (LOCAL RELIABLE STREAM)
# =========================================================

def emit_event(cur, event_type, payload):
    cur.execute("""
        INSERT INTO settlement_queue (
            id,
            transaction_id,
            wallet_id,
            amount,
            direction,
            idempotency_key,
            status,
            created_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,'PENDING',now())
    """, (
        str(uuid.uuid4()),
        payload["transaction_id"],
        payload["wallet_id"],
        payload["amount"],
        payload["direction"],
        payload["idempotency_key"]
    ))

# =========================================================
# IDENTITY / LEDGER INSERT (NO DRIFT ALLOWED)
# =========================================================

def write_ledger(cur, tx):
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
        VALUES (%s,%s,%s,%s,%s,%s,now())
        ON CONFLICT (idempotency_key) DO NOTHING
    """, (
        str(uuid.uuid4()),
        tx["transaction_id"],
        tx["wallet_id"],
        tx["direction"],
        tx["amount"],
        tx["idempotency_key"]
    ))

# =========================================================
# WALLET PROJECTION UPDATE (ONLY AFTER LEDGER WRITE)
# =========================================================

def update_wallet(cur, tx):
    if tx["direction"] == "DEBIT":
        cur.execute("""
            UPDATE wallets
            SET settled_balance = settled_balance - %s
            WHERE id=%s
        """, (tx["amount"], tx["wallet_id"]))
    else:
        cur.execute("""
            UPDATE wallets
            SET settled_balance = settled_balance + %s
            WHERE id=%s
        """, (tx["amount"], tx["wallet_id"]))

# =========================================================
# SETTLEMENT WORKER (FOR UPDATE SKIP LOCKED)
# =========================================================

def fetch_job(cur):
    cur.execute("""
        SELECT id, transaction_id, wallet_id, amount, direction, idempotency_key
        FROM settlement_queue
        WHERE status='PENDING'
        ORDER BY created_at
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    """)
    return cur.fetchone()

def mark_processing(cur, job_id):
    cur.execute("""
        UPDATE settlement_queue
        SET status='PROCESSING'
        WHERE id=%s
    """, (job_id,))

def mark_settled(cur, job_id):
    cur.execute("""
        UPDATE settlement_queue
        SET status='SETTLED'
        WHERE id=%s
    """, (job_id,))

def mark_failed(cur, job_id):
    cur.execute("""
        UPDATE settlement_queue
        SET status='FAILED',
        retry_count = retry_count + 1
        WHERE id=%s
    """, (job_id,))

# =========================================================
# INVARIANT ENGINE (HARD BLOCKER)
# =========================================================

def check_invariants(cur):
    cur.execute("""
        SELECT COUNT(*)
        FROM wallets
        WHERE settled_balance < -1000000000
    """)
    v = cur.fetchone()[0]

    if v > 0:
        raise Exception("[INVARIANT FAIL] INVALID NEGATIVE STATE DETECTED")

# =========================================================
# SETTLEMENT WORKER LOOP
# =========================================================

def worker():
    print("[OMEGA] Settlement worker online")

    while True:
        with db() as conn:
            with conn.cursor() as cur:

                job = fetch_job(cur)

                if not job:
                    time.sleep(0.2)
                    continue

                job_id, tx_id, wallet_id, amount, direction, idem = job

                try:
                    mark_processing(cur, job_id)

                    tx = {
                        "transaction_id": tx_id,
                        "wallet_id": wallet_id,
                        "amount": float(amount),
                        "direction": direction,
                        "idempotency_key": idem
                    }

                    write_ledger(cur, tx)
                    update_wallet(cur, tx)

                    check_invariants(cur)

                    mark_settled(cur, job_id)

                    conn.commit()

                except Exception as e:
                    conn.rollback()
                    mark_failed(cur, job_id)
                    conn.commit()

# =========================================================
# RECONCILIATION ENGINE (TRUTH VERIFICATION LOOP)
# =========================================================

def reconcile(conn):
    with conn.cursor() as cur:

        cur.execute("""
            SELECT w.id,
                   w.settled_balance,
                   COALESCE(SUM(
                        CASE
                            WHEN le.direction='CREDIT' THEN le.amount
                            ELSE -le.amount
                        END
                   ),0) AS ledger_balance
            FROM wallets w
            LEFT JOIN ledger_entries le
                ON w.id = le.wallet_id
            GROUP BY w.id, w.settled_balance
        """)

        mismatches = []

        for wallet_id, wallet_balance, ledger_balance in cur.fetchall():

            wallet_balance = float(wallet_balance or 0)
            ledger_balance = float(ledger_balance or 0)

            if wallet_balance != ledger_balance:
                mismatches.append((wallet_id, wallet_balance, ledger_balance))

        return mismatches

# =========================================================
# RECONCILIATION DAEMON
# =========================================================

def reconciliation_loop():
    print("[OMEGA] Reconciliation daemon online")

    while True:
        with db() as conn:

            drift = reconcile(conn)

            if drift:
                with conn.cursor() as cur:
                    for d in drift:
                        cur.execute("""
                            INSERT INTO invariant_failures (
                                invariant_name,
                                failure_details,
                                severity
                            )
                            VALUES (
                                'PROJECTION_DRIFT',
                                %s,
                                'CRITICAL'
                            )
                        """, (str(d),))

                    conn.commit()

        time.sleep(2)

# =========================================================
# MAIN ENTRY
# =========================================================

if __name__ == "__main__":
    import threading

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=reconciliation_loop)

    t1.start()
    t2.start()

    print("[OMEGA] FULL FINANCIAL EXECUTION CORE ACTIVE")

