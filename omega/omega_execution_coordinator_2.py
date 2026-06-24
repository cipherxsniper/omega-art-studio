#!/usr/bin/env python3
import json
import uuid
import psycopg2
from datetime import datetime

"""
OMEGA FINANCIAL TRUTH COORDINATOR
Single Writer Authority Layer (Stripe-style core)
"""

# ----------------------------
# STATE MACHINE (HARD RULE)
# ----------------------------
VALID_TRANSITIONS = {
    "PENDING": ["AUTHORIZED", "FAILED"],
    "AUTHORIZED": ["CAPTURED", "EXPIRED", "FAILED"],
    "CAPTURED": ["SETTLED"],
    "SETTLED": [],
    "FAILED": [],
    "EXPIRED": []
}


# ----------------------------
# ID EMPOTENCY GUARD
# ----------------------------
def check_idempotency(cur, key):
    cur.execute("""
        SELECT 1 FROM ledger_entries
        WHERE idempotency_key = %s
        LIMIT 1
    """, (key,))
    return cur.fetchone() is not None


# ----------------------------
# WALLET LOCK (SINGLE WRITER SAFETY)
# ----------------------------
def lock_wallet(cur, wallet_id):
    cur.execute("""
        SELECT id FROM wallets
        WHERE id = %s
        FOR UPDATE
    """, (wallet_id,))


# ----------------------------
# STATE VALIDATION
# ----------------------------
def validate_transition(old, new):
    if new not in VALID_TRANSITIONS.get(old, []):
        raise Exception(f"INVALID STATE TRANSITION {old} -> {new}")


# ----------------------------
# MAIN EXECUTION FUNCTION
# ----------------------------
def execute_event(conn, event):
    """
    SINGLE SOURCE OF FINANCIAL TRUTH
    """
    with conn.cursor() as cur:

        payload = event["payload"]
        idem = event["idempotency_key"]

        # 1. IDEMPOTENCY CHECK
        if check_idempotency(cur, idem):
            return {"status": "DUPLICATE_SKIPPED"}

        wallet_id = payload["wallet_id"]

        # 2. LOCK WALLET (CRITICAL SECTION)
        lock_wallet(cur, wallet_id)

        # 3. LOAD WALLET STATE
        cur.execute("""
            SELECT balance_state
            FROM wallets
            WHERE id = %s
        """, (wallet_id,))
        row = cur.fetchone()

        old_state = row[0] if row else "PENDING"

        new_state = payload.get("next_state", "AUTHORIZED")

        # 4. VALIDATE STATE MACHINE
        validate_transition(old_state, new_state)

        # 5. LEDGER INSERT (ONLY WRITER ALLOWED HERE)
        cur.execute("""
            INSERT INTO ledger_entries (
                id,
                transaction_id,
                wallet_id,
                direction,
                amount,
                idempotency_key,
                created_at
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s
            )
        """, (
            str(uuid.uuid4()),
            payload["tx"],
            wallet_id,
            payload["direction"],
            payload["amount"],
            idem,
            datetime.utcnow()
        ))

        # 6. UPDATE WALLET DERIVED STATE
        cur.execute("""
            UPDATE wallets
            SET settled_balance = COALESCE(settled_balance,0) +
                CASE WHEN %s='CREDIT' THEN %s ELSE -%s END
            WHERE id = %s
        """, (
            payload["direction"],
            payload["amount"],
            payload["amount"],
            wallet_id
        ))

        conn.commit()

        return {
            "status": "COMMITTED",
            "wallet": wallet_id,
            "state": new_state
        }
