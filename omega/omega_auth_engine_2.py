import uuid
import json
from datetime import datetime, timedelta

def authorize(conn, wallet_id, amount, idem_key):
    with conn.cursor() as cur:

        # 1. CHECK SPENDABLE
        cur.execute("""
            SELECT (settled_balance - locked_balance)
            FROM wallets
            WHERE id = %s;
        """, (wallet_id,))

        spendable = cur.fetchone()[0]

        if float(spendable) < float(amount):
            return {"status": "DECLINED", "reason": "INSUFFICIENT_FUNDS"}

        # 2. CREATE HOLD
        cur.execute("""
            INSERT INTO authorization_holds (
                wallet_id,
                amount,
                status,
                expires_at,
                idempotency_key
            )
            VALUES (%s, %s, 'AUTHORIZED', now() + interval '5 minutes', %s)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING id;
        """, (wallet_id, amount, idem_key))

        hold = cur.fetchone()
        if not hold:
            return {"status": "ALREADY_AUTHORIZED"}

        # 3. LOCK FUNDS (soft reservation)
        cur.execute("""
            UPDATE wallets
            SET locked_balance = locked_balance + %s
            WHERE id = %s;
        """, (amount, wallet_id))

        conn.commit()

        return {"status": "AUTHORIZED", "auth_id": str(hold[0])}

def capture(conn, auth_id, idem_key):
    with conn.cursor() as cur:

        # 1. GET AUTH
        cur.execute("""
            SELECT wallet_id, amount, status
            FROM authorization_holds
            WHERE id = %s;
        """, (auth_id,))

        auth = cur.fetchone()
        if not auth:
            return {"status": "NOT_FOUND"}

        wallet_id, amount, status = auth

        if status != "AUTHORIZED":
            return {"status": "INVALID_STATE"}

        # 2. MOVE TO LEDGER
        cur.execute("""
            INSERT INTO ledger_entries (
                transaction_id,
                wallet_id,
                direction,
                amount,
                idempotency_key
            )
            VALUES (%s, %s, 'DEBIT', %s, %s)
            ON CONFLICT DO NOTHING;
        """, (auth_id, wallet_id, amount, idem_key))

        # 3. RELEASE LOCKED BALANCE
        cur.execute("""
            UPDATE wallets
            SET locked_balance = locked_balance - %s,
                settled_balance = settled_balance - %s
            WHERE id = %s;
        """, (amount, amount, wallet_id))

        # 4. FINALIZE AUTH
        cur.execute("""
            UPDATE authorization_holds
            SET status = 'CAPTURED'
            WHERE id = %s;
        """, (auth_id,))

        conn.commit()

        return {"status": "CAPTURED"}
