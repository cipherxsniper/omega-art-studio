#!/usr/bin/env python3

import psycopg2
from financial_kernel_v1 import FinancialKernelV1

DB = "omega_bank"
USER = "omega"

def connect():
    return psycopg2.connect(dbname=DB, user=USER)

def main():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT event_id, sequence_number, event_type, payload, created_at
        FROM omega_events
        ORDER BY sequence_number ASC
    """)

    events = cur.fetchall()

    for event_id, seq, event_type, payload, created_at in events:

        # 🔒 KERNEL ENFORCEMENT (NO IMPROVISATION)
        if not FinancialKernelV1.is_financial_event(event_type):
            continue

        contract = FinancialKernelV1.get_posting_contract(event_type)
        if contract is None:
            continue

        payload = payload if isinstance(payload, dict) else {}

        amount = float(payload.get("amount", 0))
        account_id = payload.get("account_id")

        # 🔒 HARD GUARD (NO NULL MONEY STATE EVER)
        if account_id is None:
            print(f"BLOCKED INVALID EVENT: {event_type} {event_id}")
            continue

        for rule in contract:

            direction = rule["direction"]
            account_type = rule["account_type"]

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
                amount,
                payload.get("currency", "USD")
            ))

    conn.commit()
    cur.close()
    conn.close()

    print("KERNEL POSTINGS COMPLETE (STRICT CONTRACT MODE)")

if __name__ == "__main__":
    main()
