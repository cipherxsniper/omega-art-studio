#!/usr/bin/env python3
import psycopg2
import uuid

conn = psycopg2.connect("dbname=omega_bank user=omega")
cur = conn.cursor()

SYSTEM_ACCOUNTS = [
    ("treasury_system", str(uuid.uuid4())),
    ("clearing_system", str(uuid.uuid4())),
    ("fee_system", str(uuid.uuid4())),
]

for name, aid in SYSTEM_ACCOUNTS:
    cur.execute("""
        INSERT INTO omega_instruments (instrument_id, instrument_type, metadata)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (aid, "system_account", {"name": name}))

conn.commit()
conn.close()

print("SYSTEM ACCOUNTS INITIALIZED")
