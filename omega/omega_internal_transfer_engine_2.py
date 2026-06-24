#!/usr/bin/env python3

import psycopg2

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega",
    "host": "localhost",
    "port": 5432
}

def resolve(cur, alias):
    cur.execute("""
        SELECT wallet_id FROM wallet_registry
        WHERE alias = %s
    """, (alias,))
    row = cur.fetchone()
    if not row:
        raise Exception(f"WALLET ALIAS NOT FOUND: {alias}")
    return row[0]

def transfer(sender_alias, receiver_alias, amount):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        conn.autocommit = False

        sender = resolve(cur, sender_alias)
        receiver = resolve(cur, receiver_alias)

        cur.execute("""
            UPDATE wallets
            SET settled_balance = settled_balance - %s
            WHERE id = %s
        """, (amount, sender))

        cur.execute("""
            UPDATE wallets
            SET settled_balance = settled_balance + %s
            WHERE id = %s
        """, (amount, receiver))

        conn.commit()
        print("TRANSFER SUCCESS")

    except Exception as e:
        conn.rollback()
        print("TRANSFER FAILED:", e)

    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    transfer(sys.argv[1], sys.argv[2], float(sys.argv[3]))
