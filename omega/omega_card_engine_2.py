import uuid
import secrets

def issue_virtual_card(conn, wallet_id, spend_limit):
    with conn.cursor() as cur:

        # 1. GENERATE TOKEN (NOT REAL PAN)
        token = "vc_" + secrets.token_hex(6)

        # 2. INSERT CARD
        cur.execute("""
            INSERT INTO virtual_cards (
                wallet_id,
                card_token,
                status,
                spend_limit,
                daily_limit
            )
            VALUES (%s, %s, 'ACTIVE', %s, %s)
            RETURNING id, card_token;
        """, (wallet_id, token, spend_limit, spend_limit))

        card = cur.fetchone()

        conn.commit()

        return {
            "card_id": str(card[0]),
            "card_token": card[1],
            "status": "ACTIVE"
        }

def authorize_card_transaction(conn, card_token, amount):
    with conn.cursor() as cur:

        # 1. LOAD CARD
        cur.execute("""
            SELECT wallet_id, spend_limit, status
            FROM virtual_cards
            WHERE card_token = %s;
        """, (card_token,))

        card = cur.fetchone()
        if not card:
            return {"status": "DECLINED", "reason": "CARD_NOT_FOUND"}

        wallet_id, limit, status = card

        if status != 'ACTIVE':
            return {"status": "DECLINED", "reason": "CARD_INACTIVE"}

        # 2. CHECK WALLET SPENDABLE
        cur.execute("""
            SELECT (settled_balance - locked_balance)
            FROM wallets
            WHERE id = %s;
        """, (wallet_id,))

        spendable = cur.fetchone()[0]

        if float(amount) > float(spendable):
            return {"status": "DECLINED", "reason": "INSUFFICIENT_FUNDS"}

        if float(amount) > float(limit):
            return {"status": "DECLINED", "reason": "LIMIT_EXCEEDED"}

        # 3. CREATE AUTH HOLD
        auth_id = str(uuid.uuid4())

        cur.execute("""
            INSERT INTO authorization_holds (
                id,
                wallet_id,
                amount,
                status,
                expires_at,
                idempotency_key
            )
            VALUES (%s, %s, %s, 'AUTHORIZED', now() + interval '5 minutes', %s);
        """, (auth_id, wallet_id, amount, auth_id))

        # 4. LOCK FUNDS
        cur.execute("""
            UPDATE wallets
            SET locked_balance = locked_balance + %s
            WHERE id = %s;
        """, (amount, wallet_id))

        conn.commit()

        return {
            "status": "AUTHORIZED",
            "auth_id": auth_id,
            "wallet_id": str(wallet_id)
        }
