
import uuid
import secrets
from datetime import datetime

def create_virtual_card(conn, wallet_id, spendable_limit, idem_key):
    with conn.cursor() as cur:

        # 1. IDEMPOTENCY CHECK
        cur.execute("""
            SELECT 1 FROM virtual_cards
            WHERE card_token = %s
        """, (idem_key,))

        if cur.fetchone():
            return {"status": "ALREADY_EXISTS"}

        # 2. CARD TOKEN
        card_token = "vc_" + secrets.token_hex(8)
        card_id = str(uuid.uuid4())

        # 3. FORCE TYPE SAFETY (CRITICAL FIX)
        limit = float(spendable_limit)

        # 4. INSERT (STRICT MATCH TO SCHEMA)
        cur.execute("""
            INSERT INTO virtual_cards (
                id,
                wallet_id,
                card_token,
                masked_pan,
                expiry_month,
                expiry_year,
                cvv_hash,
                status,
                spendable_limit,
                created_at
            )
            VALUES (
                %s,%s,%s,
                '**** **** **** 4242',
                12,
                2030,
                'hashed',
                'ACTIVE',
                %s,
                now()
            )
        """, (
            card_id,
            wallet_id,
            card_token,
            limit
        ))

        conn.commit()

        return {
            "card_id": card_id,
            "wallet_id": wallet_id,
            "card_token": card_token,
            "spendable_limit": limit,
            "status": "ACTIVE",
            "created_at": datetime.utcnow().isoformat()
        }



def process_card_transaction(conn, card_token, amount, merchant, idem_key):
    import uuid
    import json

    with conn.cursor() as cur:

        # 1. IDEMPOTENCY CHECK
        cur.execute("""
            SELECT 1 FROM card_transactions
            WHERE idempotency_key = %s
        """, (idem_key,))

        if cur.fetchone():
            return {"status": "DUPLICATE_REJECTED"}

        # 2. LOAD CARD
        cur.execute("""
            SELECT wallet_id, spendable_limit, status
            FROM virtual_cards
            WHERE card_token = %s
        """, (card_token,))

        card = cur.fetchone()
        if not card:
            return {"status": "DECLINED", "reason": "CARD_NOT_FOUND"}

        wallet_id, limit, status = card

        if status != "ACTIVE":
            return {"status": "DECLINED", "reason": "CARD_INACTIVE"}

        # 3. CHECK WALLET SPENDABLE
        cur.execute("""
            SELECT (settled_balance - locked_balance)
            FROM wallets
            WHERE id = %s
        """, (wallet_id,))

        spendable = cur.fetchone()[0]

        if float(amount) > float(spendable):
            return {"status": "DECLINED", "reason": "INSUFFICIENT_FUNDS"}

        if float(amount) > float(limit):
            return {"status": "DECLINED", "reason": "LIMIT_EXCEEDED"}

        # 4. LOCK FUNDS
        cur.execute("""
            UPDATE wallets
            SET locked_balance = locked_balance + %s
            WHERE id = %s
        """, (amount, wallet_id))

        # 5. WRITE TRANSACTION
        tx_id = str(uuid.uuid4())

        cur.execute("""
            INSERT INTO card_transactions (
                id,
                card_token,
                wallet_id,
                amount,
                merchant,
                status,
                created_at,
                idempotency_key
            )
            VALUES (%s,%s,%s,%s,%s,'AUTHORIZED',now(),%s)
        """, (
            tx_id,
            card_token,
            wallet_id,
            amount,
            merchant,
            idem_key
        ))

        conn.commit()

        return {
            "status": "AUTHORIZED",
            "tx_id": tx_id,
            "amount": float(amount),
            "merchant": merchant
        }

