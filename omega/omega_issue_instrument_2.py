#!/usr/bin/env python3

import sys
import uuid
import psycopg2
import secrets

DB = "dbname=omega_bank user=omega"

def generate_instrument_token():
    # SAFE internal token (NOT payment credential)
    return "Ω-INST-" + secrets.token_hex(8).upper()

def main():
    if len(sys.argv) < 3:
        print("USAGE: omega_issue_instrument.py <wallet_id> <limit>")
        return

    wallet_id = sys.argv[1]
    limit = float(sys.argv[2])

    conn = psycopg2.connect(DB)
    cur = conn.cursor()

    instrument_id = str(uuid.uuid4())
    token = generate_instrument_token()

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
        VALUES (%s,%s,%s,'VIRTUAL_CARD',%s,'USD','ACTIVE',NOW())
    """, (instrument_id, wallet_id, token, limit))

    conn.commit()
    conn.close()

    print("INSTRUMENT_ISSUED")
    print("instrument_id:", instrument_id)
    print("instrument_token:", token)

if __name__ == "__main__":
    main()
