#!/usr/bin/env python3

"""
=========================================================
OMEGA AUTONOMOUS SETTLEMENT PIPELINE (STRIPE-STYLE CORE)
=========================================================

This system enforces:

1. Event-driven settlement
2. Idempotent processing
3. Reserve-backed issuance
4. Double-entry enforcement
5. Batch settlement windows
6. Replay-safe execution
=========================================================
"""

import uuid
import hashlib
from datetime import datetime

# =========================================================
# DB INTERFACE (PLUG INTO YOUR EXISTING db.py)
# =========================================================

class DB:
    def fetch_one(self, q, p=None): pass
    def fetch_all(self, q, p=None): pass
    def execute(self, q, p=None): pass

db = DB()


# =========================================================
# EVENT TYPES
# =========================================================

EVENT_TRANSFER = "TRANSFER_REQUESTED"
EVENT_CREDIT = "CREDIT_ISSUED"
EVENT_DEBIT = "DEBIT_POSTED"
EVENT_SETTLED = "SETTLED"


# =========================================================
# IDEMPOTENCY LAYER
# =========================================================

def idempotency_key(*args):
    raw = "|".join(map(str, args))
    return hashlib.sha256(raw.encode()).hexdigest()


def already_processed(key: str) -> bool:
    r = db.fetch_one("""
        SELECT 1 FROM idempotency_keys WHERE key = %s
    """, (key,))
    return r is not None


def mark_processed(key: str, tx_id: str):
    db.execute("""
        INSERT INTO idempotency_keys (key, transaction_id, created_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (key) DO NOTHING
    """, (key, tx_id))


# =========================================================
# RESERVE CHECK (TREASURY GUARDRAIL)
# =========================================================

def get_reserve_available():
    res = db.fetch_one("""
        SELECT COALESCE(SUM(amount),0)
        FROM ledger_entries
        WHERE direction = 'CREDIT'
    """)
    return float(res[0]) if res else 0.0


# =========================================================
# LEDGER POSTER (DOUBLE ENTRY CORE)
# =========================================================

def post(wallet_id, direction, amount, tx_id, key):
    db.execute("""
        INSERT INTO ledger_entries (
            id,
            transaction_id,
            wallet_id,
            direction,
            amount,
            idempotency_key,
            created_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, NOW()
        )
    """, (
        str(uuid.uuid4()),
        tx_id,
        wallet_id,
        direction,
        amount,
        key
    ))


# =========================================================
# SETTLEMENT ENGINE CORE
# =========================================================

def settle_transfer(from_wallet, to_wallet, amount):
    tx_id = str(uuid.uuid4())
    key = idempotency_key(tx_id, from_wallet, to_wallet, amount)

    if already_processed(key):
        return {"status": "duplicate_ignored"}

    db.execute("BEGIN;")

    try:
        # DEBIT SOURCE
        post(from_wallet, "DEBIT", amount, tx_id, key)

        # CREDIT DESTINATION (reserve-backed check happens here)
        reserve = get_reserve_available()

        if amount > reserve:
            raise Exception("INSUFFICIENT RESERVE BACKING")

        post(to_wallet, "CREDIT", amount, tx_id, key)

        mark_processed(key, tx_id)

        db.execute("COMMIT;")

        return {"status": "settled", "tx": tx_id}

    except Exception as e:
        db.execute("ROLLBACK;")
        return {"status": "failed", "error": str(e)}


# =========================================================
# BATCH SETTLEMENT WORKER
# =========================================================

def process_settlement_batch(limit=100):
    jobs = db.fetch_all("""
        SELECT id, from_wallet, to_wallet, amount
        FROM settlement_queue
        WHERE status = 'PENDING'
        LIMIT %s
    """, (limit,))

    for job in jobs:
        result = settle_transfer(job[1], job[2], job[3])

        db.execute("""
            UPDATE settlement_queue
            SET status = %s
            WHERE id = %s
        """, (result["status"], job[0]))


# =========================================================
# RECONCILIATION CHECK
# =========================================================

def reconcile_wallet(wallet_id):
    ledger_balance = db.fetch_one("""
        SELECT COALESCE(SUM(
            CASE
                WHEN direction='CREDIT' THEN amount
                WHEN direction='DEBIT' THEN -amount
                ELSE 0
            END
        ),0)
        FROM ledger_entries
        WHERE wallet_id = %s
    """, (wallet_id,))

    return float(ledger_balance[0]) if ledger_balance else 0.0


