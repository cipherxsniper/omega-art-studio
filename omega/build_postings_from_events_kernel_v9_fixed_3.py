#!/usr/bin/env python3

import psycopg2

DB = "omega_bank"
USER = "omega"

SYSTEM_ACCOUNT = "00000000-0000-0000-0000-000000000000"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)


def insert(cur, event_id, seq, account_type, account_id, direction, amount):
    cur.execute("""
        INSERT INTO ledger_postings
        (event_id, sequence_number, account_type, account_id, direction, amount, currency)
        VALUES (%s,%s,%s,%s,%s,%s,'USD')
    """, (event_id, seq, account_type, account_id, direction, float(amount)))


def handle_event(cur, event_id, seq, event_type, payload):

    amount = payload.get("amount")
    wallet_id = payload.get("wallet_id")
    merchant_id = payload.get("merchant_id")

    if amount is None:
        return

    amount = float(amount)

    # =========================
    # STRICT SINGLE DISPATCH ONLY
    # =========================

    if event_type == "AUTH_CREATED":

        insert(cur, event_id, seq, "wallet", wallet_id, "CREDIT", amount)
        insert(cur, event_id, seq, "system", SYSTEM_ACCOUNT, "DEBIT", amount)

    elif event_type == "AUTH_CAPTURED":

        insert(cur, event_id, seq, "wallet", wallet_id, "DEBIT", amount)
        insert(cur, event_id, seq, "system", SYSTEM_ACCOUNT, "CREDIT", amount)

    elif event_type == "AUTH_REVERSED":

        insert(cur, event_id, seq, "system", SYSTEM_ACCOUNT, "DEBIT", amount)
        insert(cur, event_id, seq, "wallet", wallet_id, "CREDIT", amount)

    elif event_type == "AUTH_EXPIRED":

        insert(cur, event_id, seq, "system", SYSTEM_ACCOUNT, "DEBIT", amount)
        insert(cur, event_id, seq, "wallet", wallet_id, "CREDIT", amount)

    elif event_type == "PAYMENT_CAPTURED":

        insert(cur, event_id, seq, "wallet", wallet_id, "DEBIT", amount)
        insert(cur, event_id, seq, "merchant", merchant_id, "CREDIT", amount)

    else:
        # 🔥 CRITICAL: NO FALLBACK HANDLING
        print(f"SKIP UNKNOWN EVENT TYPE: {event_type}")


def main():

    conn = connect()
    cur = conn.cursor()

    # 🔥 IMPORTANT: CLEAN STATE BEFORE REBUILD (prevents accumulation)
    cur.execute("DELETE FROM ledger_postings;")

    cur.execute("""
        SELECT event_id, sequence_number, event_type, payload
        FROM omega_events
        ORDER BY sequence_number ASC
    """)

    events = cur.fetchall()

    seen = set()

    for event_id, seq, event_type, payload in events:

        # 🔥 HARD IDEMPOTENCY GUARD
        if event_id in seen:
            print(f"SKIP DUPLICATE EVENT: {event_id}")
            continue

        seen.add(event_id)

        handle_event(cur, event_id, seq, event_type, payload)

    conn.commit()
    cur.close()
    conn.close()

    print("POSTINGS BUILT (V9 FIXED DETERMINISTIC)")


if __name__ == "__main__":
    main()
