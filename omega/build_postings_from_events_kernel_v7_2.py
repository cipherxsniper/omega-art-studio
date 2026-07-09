#!/usr/bin/env python3

import psycopg2

DB = "omega_bank"
USER = "omega"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)


def insert(cur, event_id, seq, account_type, account_id, direction, amount, currency):
    cur.execute("""
        INSERT INTO ledger_postings
        (event_id, sequence_number, account_type, account_id, direction, amount, currency)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        event_id, seq, account_type, account_id, direction, float(amount), currency
    ))


def main():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT event_id, sequence_number, event_type, payload
        FROM omega_events
        ORDER BY sequence_number ASC
    """)

    events = cur.fetchall()

    for event_id, seq, event_type, payload in events:

        amount = payload.get("amount")
        wallet_id = payload.get("wallet_id")
        merchant_id = payload.get("merchant_id")
        currency = payload.get("currency", "USD")

        if amount is None:
            continue

        # =========================
        # 🔥 DOUBLE ENTRY RULES
        # =========================

        if event_type == "AUTH_CREATED":
            # wallet gets CREDIT, system gets DEBIT
            insert(cur, event_id, seq, "wallet", wallet_id, "CREDIT", amount, currency)
            insert(cur, event_id, seq, "system", "00000000-0000-0000-0000-000000000000", "DEBIT", amount, currency)

        elif event_type == "AUTH_CAPTURED":
            insert(cur, event_id, seq, "wallet", wallet_id, "DEBIT", amount, currency)
            insert(cur, event_id, seq, "system", "00000000-0000-0000-0000-000000000000", "CREDIT", amount, currency)

        elif event_type == "AUTH_REVERSED":
            insert(cur, event_id, seq, "system", "00000000-0000-0000-0000-000000000000", "DEBIT", amount, currency)
            insert(cur, event_id, seq, "wallet", wallet_id, "CREDIT", amount, currency)

        elif event_type == "AUTH_EXPIRED":
            insert(cur, event_id, seq, "system", "00000000-0000-0000-0000-000000000000", "DEBIT", amount, currency)
            insert(cur, event_id, seq, "wallet", wallet_id, "CREDIT", amount, currency)

        elif event_type == "PAYMENT_CAPTURED":
            # merchant receives CREDIT, wallet pays DEBIT
            insert(cur, event_id, seq, "wallet", wallet_id, "DEBIT", amount, currency)
            insert(cur, event_id, seq, "merchant", merchant_id, "CREDIT", amount, currency)

    conn.commit()
    cur.close()
    conn.close()

    print("POSTINGS BUILT (TRUE DOUBLE ENTRY V7)")


if __name__ == "__main__":
    main()
