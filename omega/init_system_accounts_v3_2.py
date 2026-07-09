#!/usr/bin/env python3

import psycopg2
from uuid import UUID

DB = "omega_bank"
USER = "omega"

SYSTEM_ACCOUNT_ID = UUID("00000000-0000-0000-0000-000000000000")

def connect():
    return psycopg2.connect(dbname=DB, user=USER)

def create_system_accounts():
    conn = connect()
    cur = conn.cursor()

    accounts = [
        (str(SYSTEM_ACCOUNT_ID), "treasury"),
        (str(UUID("11111111-1111-1111-1111-111111111111")), "merchant_reserve"),
        (str(UUID("22222222-2222-2222-2222-222222222222")), "wallet_settlement")
    ]

    for aid, atype in accounts:

        cur.execute("""
            INSERT INTO omega_instruments (instrument_id, instrument_type)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (aid, atype))

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    create_system_accounts()
    print("SYSTEM ACCOUNTS INITIALIZED (SCHEMA ALIGNED)")
