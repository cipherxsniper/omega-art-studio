"""
OMEGA AUTH / CAPTURE / SETTLEMENT ENGINE
Processor-grade state machine (sandbox ledger system)
"""

import uuid
import time
import psycopg2


# -----------------------------
# AUTHORIZATION (RESERVE ONLY)
# -----------------------------
def authorize_payment(conn, wallet_id, amount, merchant):
    with conn.cursor() as cur:

        # lock + check available funds
        cur.execute("""
            SELECT settled_balance, locked_balance
            FROM wallets
            WHERE id = %s
            FOR UPDATE
        """, (wallet_id,))

        settled, locked = cur.fetchone()
        available = float(settled) - float(locked)

        if amount > available:
            raise Exception("AUTH_FAILED_INSUFFICIENT_FUNDS")

        # create hold
        transaction_id = str(uuid.uuid4())

        cur.execute("""
            INSERT INTO authorization_holds (
                id,
                transaction_id,
                wallet_id,
                amount,
                status,
                merchant_name,
                created_at
            )
            VALUES (
                gen_random_uuid(),
                %s,
                %s,
                %s,
                'AUTHORIZED',
                %s,
                now()
            )
        """, (transaction_id, wallet_id, amount, merchant))

        # lock funds
        cur.execute("""
            UPDATE wallets
            SET locked_balance = locked_balance + %s
            WHERE id = %s
        """, (amount, wallet_id))

        conn.commit()

        return transaction_id


# -----------------------------
# CAPTURE (FINALIZE LEDGER)
# -----------------------------
def capture_payment(conn, transaction_id):
    with conn.cursor() as cur:

        cur.execute("""
            SELECT wallet_id, amount, status
            FROM authorization_holds
            WHERE transaction_id = %s
            FOR UPDATE
        """, (transaction_id,))

        row = cur.fetchone()
        if not row:
            raise Exception("CAPTURE_FAILED_HOLD_NOT_FOUND")

        wallet_id, amount, status = row

        if status != "AUTHORIZED":
            raise Exception("CAPTURE_INVALID_STATE")

        # ledger debit (final truth)
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
        """, (
            transaction_id,
            wallet_id,
            amount,
            f"capture-{transaction_id}"
        ))

        # mark captured
        cur.execute("""
            UPDATE authorization_holds
            SET status = 'CAPTURED'
            WHERE transaction_id = %s
        """, (transaction_id,))

        conn.commit()

        return True


# -----------------------------
# SETTLEMENT FINALIZATION
# -----------------------------
def settle_payment(conn, transaction_id):
    with conn.cursor() as cur:

        cur.execute("""
            SELECT wallet_id, amount
            FROM authorization_holds
            WHERE transaction_id = %s
        """, (transaction_id,))

        row = cur.fetchone()
        if not row:
            raise Exception("SETTLEMENT_FAILED_NOT_FOUND")

        wallet_id, amount = row

        # release lock + finalize balances
        cur.execute("""
            UPDATE wallets
            SET locked_balance = locked_balance - %s,
                settled_balance = settled_balance - %s
            WHERE id = %s
        """, (amount, amount, wallet_id))

        conn.commit()

        return True
