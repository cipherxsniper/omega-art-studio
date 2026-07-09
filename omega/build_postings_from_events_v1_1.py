#!/usr/bin/env python3

import psycopg2

conn = psycopg2.connect("dbname=omega_bank user=omega")
cur = conn.cursor()

cur.execute("""
SELECT event_id, event_type, payload, sequence_number
FROM omega_events
ORDER BY sequence_number ASC
""")

events = cur.fetchall()

def emit_postings(event_id, event_type, payload, seq):
    postings = []

    amount = payload.get("amount", 0)
    wallet_id = payload.get("wallet_id")
    merchant_id = payload.get("merchant_id")

    if event_type == "AUTH_CREATED":
        postings.append((event_id, seq, "wallet", wallet_id, "CREDIT", amount))
        postings.append((event_id, seq, "treasury", "SYSTEM", "DEBIT", amount))

    elif event_type == "PAYMENT_CAPTURED":
        postings.append((event_id, seq, "wallet", wallet_id, "DEBIT", amount))
        postings.append((event_id, seq, "merchant", merchant_id, "CREDIT", amount))

    elif event_type == "AUTH_REVERSED":
        postings.append((event_id, seq, "wallet", wallet_id, "DEBIT", amount))
        postings.append((event_id, seq, "treasury", "SYSTEM", "CREDIT", amount))

    elif event_type == "AUTH_EXPIRED":
        postings.append((event_id, seq, "wallet", wallet_id, "DEBIT", amount))
        postings.append((event_id, seq, "treasury", "SYSTEM", "CREDIT", amount))

    return postings

for event_id, event_type, payload, seq in events:
    for p in emit_postings(event_id, event_type, payload, seq):
        cur.execute("""
            INSERT INTO ledger_postings
            (event_id, sequence_number, account_type, account_id, direction, amount)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, p)

conn.commit()
cur.close()
conn.close()

print("LEDGER POSTINGS BUILT")
