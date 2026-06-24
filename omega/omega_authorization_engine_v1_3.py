import psycopg2
from decimal import Decimal

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "password": "omega",
    "host": "localhost"
}

def conn():
    c = psycopg2.connect(**DB_CONFIG)
    c.autocommit = False
    return c


def authorize(instrument_token, amount):
    c = conn()
    cur = c.cursor()

    cur.execute("""
        SELECT wallet_id, spend_limit, status
        FROM omega_instruments
        WHERE instrument_token = %s
        FOR UPDATE
    """, (instrument_token,))

    row = cur.fetchone()

    if not row:
        c.rollback()
        return {"status": "DECLINED", "reason": "UNKNOWN_INSTRUMENT"}

    wallet_id, limit, status = row

    if status != "ACTIVE":
        c.rollback()
        return {"status": "DECLINED", "reason": "INACTIVE"}

    cur.execute("""
        SELECT (settled_balance - reserved_balance - pending_balance)
        FROM wallets
        WHERE id = %s
        FOR UPDATE
    """, (wallet_id,))

    available = cur.fetchone()[0]

    if Decimal(available) < Decimal(amount):
        c.rollback()
        return {"status": "DECLINED", "reason": "INSUFFICIENT_FUNDS"}

    cur.execute("""
        UPDATE wallets
        SET reserved_balance = reserved_balance + %s
        WHERE id = %s
    """, (amount, wallet_id))

    c.commit()
    c.close()

    return {
        "status": "APPROVED",
        "amount": float(amount),
        "instrument": instrument_token
    }


if __name__ == "__main__":
    import sys
    print(authorize(sys.argv[1], sys.argv[2]))
