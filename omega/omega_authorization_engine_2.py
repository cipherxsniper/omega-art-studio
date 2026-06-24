#!/usr/bin/env python3
import sys
import psycopg2

def authorize(token, amount):
    conn = psycopg2.connect("dbname=omega_bank user=omega")
    cur = conn.cursor()

    cur.execute("""
        SELECT wallet_id, spend_limit
        FROM omega_instruments
        WHERE instrument_token = %s AND status='ACTIVE'
    """, (token,))

    row = cur.fetchone()

    if not row:
        print({"status":"DECLINED","reason":"UNKNOWN_INSTRUMENT"})
        return

    wallet_id, limit = row

    cur.execute("""
        SELECT settled_balance - reserved_balance
        FROM wallets
        WHERE id = %s
    """, (wallet_id,))

    available = cur.fetchone()[0]

    if available < amount:
        print({"status":"DECLINED","reason":"INSUFFICIENT_FUNDS"})
        return

    cur.execute("""
        UPDATE wallets
        SET reserved_balance = reserved_balance + %s
        WHERE id = %s
    """, (amount, wallet_id))

    conn.commit()
    conn.close()

    print({
        "status": "APPROVED",
        "amount": amount,
        "wallet": wallet_id,
        "instrument": token
    })

if __name__ == "__main__":
    authorize(sys.argv[1], float(sys.argv[2]))
