import psycopg2
import uuid
import json
from decimal import Decimal

def authorize(instrument_token, amount, conn, idempotency_key):

    cur = conn.cursor()

    # 1. Resolve instrument → wallet
    cur.execute("""
        SELECT wallet_id
        FROM omega_instruments
        WHERE instrument_token = %s AND status = 'ACTIVE'
    """, (instrument_token,))

    row = cur.fetchone()
    if not row:
        return {"status": "DECLINED", "reason": "UNKNOWN_INSTRUMENT"}

    wallet_id = row[0]

    # 2. Load wallet projection
    cur.execute("""
        SELECT settled_balance, reserved_balance, pending_balance
        FROM wallet_state_projection
        WHERE wallet_id = %s
        FOR UPDATE
    """, (wallet_id,))

    w = cur.fetchone()
    if not w:
        return {"status": "DECLINED", "reason": "WALLET_NOT_FOUND"}

    settled, reserved, pending = map(Decimal, w)
    available = settled - reserved - pending

    if available < Decimal(amount):
        return {"status": "DECLINED", "reason": "INSUFFICIENT_FUNDS"}

    # 3. Emit ledger event (NO direct mutation)
    cur.execute("""
        INSERT INTO ledger_events (
            event_type,
            aggregate_id,
            aggregate_type,
            payload,
            idempotency_key
        )
        VALUES (
            'AUTH_HOLD',
            %s,
            'WALLET',
            %s,
            %s
        )
    """, (
        wallet_id,
        json.dumps({"amount": str(amount)}),
        idempotency_key
    ))

    conn.commit()

    return {
        "status": "APPROVED",
        "wallet_id": str(wallet_id),
        "amount": str(amount)
    }
