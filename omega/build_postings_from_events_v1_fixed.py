#!/usr/bin/env python3
import psycopg2
from fix_system_account_mapping_v1 import resolve_account_id

conn = psycopg2.connect("dbname=omega_bank user=omega")
cur = conn.cursor()

cur.execute("SELECT event_id, sequence_number, payload FROM omega_events ORDER BY sequence_number")
events = cur.fetchall()

for event_id, seq, payload in events:

    postings = payload.get("postings", [])

    for p in postings:
        account_id = resolve_account_id(p["account_id"], cur)

        cur.execute("""
            INSERT INTO ledger_postings
            (event_id, sequence_number, account_type, account_id, direction, amount)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            event_id,
            seq,
            p["account_type"],
            account_id,
            p["direction"],
            p["amount"]
        ))

conn.commit()
conn.close()

print("POSTINGS BUILT CLEANLY (SYSTEM SAFE)")
