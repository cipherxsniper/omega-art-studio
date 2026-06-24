import psycopg2
import uuid
import json
from decimal import Decimal

DB = {
    "dbname": "omega_bank",
    "user": "omega",
    "password": "omega",
    "host": "localhost"
}

def conn():
    c = psycopg2.connect(**DB)
    c.autocommit = False
    return c


def authorize(instrument_token, amount, idempotency_key):
    c = conn()
    cur = c.cursor()

    # 1. lookup instrument
    cur.execute("""
        SELECT wallet_id, status
        FROM omega_instruments
        WHERE instrument_token = %s
        FOR UPDATE
    """, (instrument_token,))

    inst = cur.fetchone()

    if not inst:
        return {"status": "DECLINED", "reason": "UNKNOWN_INSTRUMENT"}

    wallet_id, status = inst

    if status != "ACTIVE":
        return {"status": "DECLINED", "reason": "INACTIVE"}

    # 2. compute available balance (projection logic)
    cur.execute("""
        SELECT settled_balance - reserved_balance - pending_balance
        FROM wallet_state_projection
        WHERE wallet_id = %s
    """, (wallet_id,))

    row = cur.fetchone()
    available = Decimal(row[0])

    if available < Decimal(amount):
        return {"status": "DECLINED", "reason": "INSUFFICIENT_FUNDS"}

    # 3. emit AUTH event (NO DIRECT UPDATE)
    cur.execute("""
        INSERT INTO omega_events (
            event_id,
            event_type,
            aggregate_id,
            aggregate_type,
            payload,
            idempotency_key
        )
        VALUES (%s,'AUTH_APPROVED',%s,'WALLET',%s,%s)
    """, (
        str(uuid.uuid4()),
        wallet_id,
        json.dumps({"amount": float(amount)}),
        idempotency_key
    ))

    c.commit()
    c.close()

    return {"status": "APPROVED", "amount": float(amount)}
