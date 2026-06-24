import uuid
import psycopg2
from decimal import Decimal
from datetime import datetime

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "password": "omega",
    "host": "localhost"
}

def get_conn():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    return conn


def issue_instrument(wallet_id, spend_limit, currency="OMEGA_USD"):
    conn = get_conn()
    cur = conn.cursor()

    instrument_id = str(uuid.uuid4())
    instrument_token = f"Ω-{uuid.uuid4().hex[:16].upper()}"

    cur.execute("""
        INSERT INTO omega_instruments (
            instrument_id,
            wallet_id,
            instrument_token,
            instrument_type,
            spend_limit,
            currency,
            status,
            created_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,'ACTIVE',NOW())
    """, (
        instrument_id,
        wallet_id,
        instrument_token,
        "VIRTUAL_CARD",
        spend_limit,
        currency
    ))

    conn.commit()
    conn.close()

    return {
        "instrument_id": instrument_id,
        "instrument_token": instrument_token,
        "status": "ACTIVE"
    }


if __name__ == "__main__":
    import sys
    wallet_id = sys.argv[1]
    limit = Decimal(sys.argv[2])
    print(issue_instrument(wallet_id, limit))
