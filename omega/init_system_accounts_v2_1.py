#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import Json
from uuid import UUID

DB = "omega_bank"
USER = "omega"

SYSTEM_ACCOUNT_ID = UUID("00000000-0000-0000-0000-000000000000")

def connect():
    return psycopg2.connect(
        dbname=DB,
        user=USER
    )

def create_system_accounts():
    conn = connect()
    cur = conn.cursor()

    accounts = [
        (SYSTEM_ACCOUNT_ID, "treasury", "Treasury System Account"),
        (UUID("11111111-1111-1111-1111-111111111111"), "merchant_reserve", "Merchant Reserve"),
        (UUID("22222222-2222-2222-2222-222222222222"), "wallet_settlement", "Wallet Settlement")
    ]

    for aid, atype, name in accounts:
        cur.execute("""
            INSERT INTO omega_instruments (instrument_id, instrument_type, metadata)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (aid, atype, Json({"name": name})))

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    create_system_accounts()
    print("SYSTEM ACCOUNTS INITIALIZED")
