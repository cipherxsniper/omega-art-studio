#!/usr/bin/env python3

"""
=========================================================
OMEGA SETTLEMENT ORCHESTRATOR v1
Stripe-style core banking execution engine
=========================================================

Components:
- Settlement Queue Engine
- Double-entry Ledger Writer
- Treasury Guard
- Idempotency Protection
- Worker Loop
=========================================================
"""

import uuid
import json
import time
import psycopg2

DB_DSN = "dbname=omega_bank"

# =========================
# DATABASE CONNECTION
# =========================

def db():
    return psycopg2.connect(DB_DSN)

# =========================
# IDEMPOTENCY CHECK
# =========================

def is_duplicate(key):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM settlement_queue
                WHERE idempotency_key = %s
            """, (key,))
            return cur.fetchone() is not None

# =========================
# TREASURY CHECK
# =========================

def treasury_ok(amount):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT available_balance
                FROM treasury_state
                WHERE asset_type = 'USD'
            """)
            row = cur.fetchone()
            if not row:
                return False
            return float(row[0]) >= float(amount)

# =========================
# QUEUE EVENT
# =========================

def enqueue(event_type, payload, idem_key):
    if is_duplicate(idem_key):
        return

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO settlement_queue
                (id, event_type, status, payload, idempotency_key)
                VALUES (%s,%s,'PENDING',%s,%s)
            """, (
                str(uuid.uuid4()),
                event_type,
                json.dumps(payload),
                idem_key
            ))
        conn.commit()

# =========================
# LEDGER WRITER
# =========================

def ledger_write(tx_id, wallet_id, direction, amount, idem):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ledger_entries
                (id, transaction_id, wallet_id, direction, amount, idempotency_key)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                str(uuid.uuid4()),
                tx_id,
                wallet_id,
                direction,
                float(amount),
                idem
            ))
        conn.commit()

# =========================
# SETTLEMENT ENGINE
# =========================

def process(job):
    tx_id = str(uuid.uuid4())
    payload = job["payload"]
    event = job["event_type"]

    amount = float(payload["amount"])
    wallet = payload["wallet_id"]

    if not treasury_ok(amount):
        raise Exception("INSUFFICIENT TREASURY")

    if event == "CREDIT_ISSUED":
        ledger_write(tx_id, "OMEGA_TREASURY", "DEBIT", amount, f"{tx_id}-t")
        ledger_write(tx_id, wallet, "CREDIT", amount, f"{tx_id}-u")

    elif event == "WITHDRAWAL":
        ledger_write(tx_id, wallet, "DEBIT", amount, f"{tx_id}-u")
        ledger_write(tx_id, "OMEGA_TREASURY", "CREDIT", amount, f"{tx_id}-t")

    return tx_id

# =========================
# WORKER LOOP
# =========================

def fetch_jobs():
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, event_type, payload, idempotency_key
                FROM settlement_queue
                WHERE status='PENDING'
                LIMIT 10
            """)
            rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "event_type": r[1],
            "payload": r[2],
            "idempotency_key": r[3]
        }
        for r in rows
    ]


def mark(job_id, status):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE settlement_queue
                SET status=%s, updated_at=NOW()
                WHERE id=%s
            """, (status, job_id))
        conn.commit()


def worker():
    print("[OMEGA] Settlement engine started")

    while True:
        jobs = fetch_jobs()

        for job in jobs:
            try:
                mark(job["id"], "PROCESSING")
                process(job)
                mark(job["id"], "SETTLED")
            except Exception as e:
                print("[ERROR]", e)
                mark(job["id"], "FAILED")

        time.sleep(1)


if __name__ == "__main__":
    worker()

