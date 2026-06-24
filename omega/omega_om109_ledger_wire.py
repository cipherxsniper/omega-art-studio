#!/usr/bin/env python3
import sys
sys.path.insert(0, '/data/data/com.termux/files/home')
import psycopg2
import omega_om109 as om109

chain = om109._load_chain()

conn = psycopg2.connect(host="127.0.0.1", port=5432,
                        user="postgres", dbname="omega_bank")
conn.autocommit = True
cur = conn.cursor()

cur.execute("""
    SELECT id, transaction_id, amount, debit_account, credit_account
    FROM ledger_entries
    WHERE om109_fingerprint IS NULL
    AND event_type NOT IN ('STRESS_TEST','STRESS_BILLION')
    ORDER BY global_sequence DESC
    LIMIT 5
""")
rows = cur.fetchall()

for row in rows:
    data = f"{row[0]}:{row[1]}:{row[2]}:{row[3]}:{row[4]}"
    result = om109.sign(data, chain)
    fp = result['fingerprint']
    cur.execute("UPDATE ledger_entries SET om109_fingerprint=%s WHERE id=%s",
                (fp, row[0]))
    print(f"Signed: {str(row[0])[:8]}... fp={fp[:20]}...")

om109._save_chain(chain)
print(f"Chain position: {chain['position']}")
conn.close()
