import uuid
import psycopg2
from decimal import Decimal

conn = psycopg2.connect("dbname=omega_bank user=omega")
cur = conn.cursor()

def authorize(instrument_token, amount, idempotency_key):
    cur.execute("""
        SELECT wallet_id, status
        FROM omega_instruments
        WHERE instrument_token = %s
    """, (instrument_token,))

    row = cur.fetchone()

    if not row:
        return {"status": "DECLINED", "reason": "UNKNOWN_INSTRUMENT"}

    wallet_id, status = row

    if status != "ACTIVE":
        return {"status": "DECLINED", "reason": "INACTIVE"}

    cur.execute("""
        SELECT settled_balance - reserved_balance - pending_balance
        FROM wallets
        WHERE id = %s
        FOR UPDATE
    """, (wallet_id,))

    available = Decimal(cur.fetchone()[0])

    if available < Decimal(amount):
        return {"status": "DECLINED", "reason": "INSUFFICIENT_FUNDS"}

    cur.execute("""
        INSERT INTO settlement_queue (
            id, event_type, status, payload,
            created_at, updated_at, retry_count,
            auth_id, wallet_id, amount
        ) VALUES (
            %s, 'AUTH_HOLD', 'PENDING',
            %s::jsonb,
            NOW(), NOW(), 0,
            %s, %s, %s
        )
    """, (
        str(uuid.uuid4()),
        '{"type":"AUTH_HOLD"}',
        str(uuid.uuid4()),
        wallet_id,
        amount
    ))

    conn.commit()

    return {"status": "APPROVED"}

