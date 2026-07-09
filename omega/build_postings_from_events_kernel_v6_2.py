#!/usr/bin/env python3

import psycopg2

DB = "omega_bank"
USER = "omega"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)

# 🔥 CANONICAL EVENT → POSTING RULES
def map_event(event_type, payload):

    amount = payload.get("amount")
    wallet_id = payload.get("wallet_id")
    merchant_id = payload.get("merchant_id")
    currency = payload.get("currency", "USD")

    if amount is None:
        return None

    # AUTH FLOWS
    if event_type == "AUTH_CREATED":
        return ("wallet", wallet_id, "CREDIT", amount, currency)

    if event_type == "AUTH_CAPTURED":
        return ("wallet", wallet_id, "DEBIT", amount, currency)

    if event_type == "AUTH_REVERSED":
        return ("wallet", wallet_id, "CREDIT", amount, currency)

    if event_type == "AUTH_EXPIRED":
        return ("wallet", wallet_id, "CREDIT", amount, currency)

    # PAYMENT FLOW
    if event_type == "PAYMENT_CAPTURED":
        return ("merchant", merchant_id, "CREDIT", amount, currency)

    return None


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

        result = map_event(event_type, payload)

        if result is None:
            print(f"SKIP EVENT (no mapping): {event_type} {event_id}")
            continue

        account_type, account_id, direction, amount, currency = result

        cur.execute("""
            INSERT INTO ledger_postings
            (event_id, sequence_number, account_type, account_id, direction, amount, currency)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            event_id,
            seq,
            account_type,
            account_id,
            direction,
            float(amount),
            currency
        ))

    conn.commit()
    cur.close()
    conn.close()

    print("POSTINGS BUILT (CANONICAL CONTRACT ENGINE V6)")


if __name__ == "__main__":
    main()
