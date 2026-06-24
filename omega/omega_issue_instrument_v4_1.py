import uuid
import secrets
import psycopg2

conn = psycopg2.connect("dbname=omega_bank user=omega")
cur = conn.cursor()

def issue(wallet_id, limit):
    instrument_id = str(uuid.uuid4())

    token = "Ω-INSTR-" + secrets.token_hex(8).upper()

    cur.execute("""
        INSERT INTO omega_instruments (
            instrument_id,
            wallet_id,
            instrument_token,
            instrument_type,
            status,
            spend_limit
        )
        VALUES (%s, %s, %s, 'VIRTUAL_CARD', 'ACTIVE', %s)
    """, (instrument_id, wallet_id, token, limit))

    conn.commit()

    print({
        "instrument_id": instrument_id,
        "instrument_token": token,
        "wallet_id": wallet_id,
        "limit": float(limit),
        "status": "ACTIVE"
    })

if __name__ == "__main__":
    import sys
    issue(sys.argv[1], sys.argv[2])
