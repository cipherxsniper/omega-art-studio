#!/usr/bin/env python3

import psycopg2

DB = "omega_bank"
USER = "omega"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)

def normalize_direction(d):
    d = d.lower()
    if d == "debit":
        return "DEBIT"
    if d == "credit":
        return "CREDIT"
    raise Exception(f"Invalid direction: {d}")

def is_financial_event(event_type):
    return event_type in [
        "PAYMENT_CAPTURED",
        "SETTLEMENT_POSTED",
        "TRANSFER_POSTED"
    ]

def main():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            event_id,
            sequence_number,
            event_type,
            payload,
            created_at
        FROM omega_events
        ORDER BY sequence_number ASC
    """)

    events = cur.fetchall()

    for e in events:
        event_id, seq, event_type, payload, created_at = e

        # 🔥 CRITICAL FIX: only financial events generate ledger postings
        if not is_financial_event(event_type):
            continue

        payload = payload if isinstance(payload, dict) else {}

        account_id = payload.get("account_id")

        # safety guard (no NULL inserts)
        if account_id is None:
            print(f"SKIP EVENT (missing account_id): {event_type} {event_id}")
            continue

        amount = float(payload.get("amount", 0))

        direction = "DEBIT" if "DEBIT" in event_type else "CREDIT"

        cur.execute("""
            INSERT INTO ledger_postings
            (event_id, sequence_number, account_type, account_id, direction, amount, currency)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            event_id,
            seq,
            event_type,
            account_id,
            direction,
            amount,
            payload.get("currency", "USD")
        ))

    conn.commit()
    cur.close()
    conn.close()

    print("POSTINGS BUILT CLEANLY (FINANCIAL EVENTS ONLY)")

if __name__ == "__main__":
    main()
