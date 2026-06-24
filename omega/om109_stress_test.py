#!/usr/bin/env python3
"""
OM109 Real Stress Test v2 — resilient to WiFi drops
Reconnects automatically if the connection dies mid-batch,
resumes from where it left off instead of crashing.
"""
import psycopg2
import time
import uuid
import sys

WALLET_ID = "7597e069-65bc-4b55-b420-a2a2682f53e0"
BATCH_SIZE = 200
TOTAL = 10000
MAX_RETRIES_PER_BATCH = 5

def get_conn():
    return psycopg2.connect(
        host="127.0.0.1", port=5432, dbname="omega_bank", user="postgres",
        connect_timeout=10,
        keepalives=1, keepalives_idle=5, keepalives_interval=2, keepalives_count=3
    )

def insert_batch(conn, batch_start, batch_size):
    cur = conn.cursor()
    rows = []
    for i in range(batch_size):
        rows.append((
            str(uuid.uuid4()), str(uuid.uuid4()), WALLET_ID, "DEBIT", 0.01,
            str(uuid.uuid4()), "OM109_STRESS_TEST_REAL",
            "stress_test_account", "stress_test_account",
            f"stress_test_payload_{batch_start+i}", False,
        ))
    cur.executemany("""
        INSERT INTO ledger_entries
        (id, transaction_id, wallet_id, direction, amount, idempotency_key,
         event_type, debit_account, credit_account, memo, wallet_required)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, rows)
    conn.commit()
    cur.close()

def run():
    print(f"Starting {TOTAL} real ledger inserts in batches of {BATCH_SIZE} (resilient to WiFi drops)...")
    start = time.time()
    inserted = 0
    conn = get_conn()
    wifi_drops = 0

    for batch_start in range(0, TOTAL, BATCH_SIZE):
        retries = 0
        while retries < MAX_RETRIES_PER_BATCH:
            try:
                insert_batch(conn, batch_start, BATCH_SIZE)
                inserted += BATCH_SIZE
                break
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                retries += 1
                wifi_drops += 1
                print(f"  Connection dropped at batch {batch_start} (retry {retries}/{MAX_RETRIES_PER_BATCH}): {e}")
                time.sleep(2)
                try:
                    conn.close()
                except Exception:
                    pass
                conn = get_conn()
        if retries >= MAX_RETRIES_PER_BATCH:
            print(f"  FAILED batch at {batch_start} after {MAX_RETRIES_PER_BATCH} retries — stopping")
            break
        if inserted % 2000 == 0:
            elapsed = time.time() - start
            print(f"  {inserted}/{TOTAL} inserted ({inserted/elapsed:.1f} tx/sec so far, {wifi_drops} reconnects)")

    elapsed = time.time() - start
    print(f"\nDONE. {inserted} entries inserted in {elapsed:.2f}s")
    print(f"Real database TPS: {inserted/elapsed:.2f}")
    print(f"WiFi/connection drops survived: {wifi_drops}")

    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*), COUNT(DISTINCT om109_fingerprint), COUNT(DISTINCT chain_hash)
        FROM ledger_entries WHERE event_type = 'OM109_STRESS_TEST_REAL'
    """)
    total, unique_om109, unique_sha = cur.fetchone()
    print(f"\nVerification:")
    print(f"  Total entries:        {total}")
    print(f"  Unique OM109 fingerprints: {unique_om109}")
    print(f"  Unique SHA256 chain hashes: {unique_sha}")
    if unique_om109 == total:
        print(f"  ✅ ZERO OM109 collisions across {total} real inserts")
    else:
        print(f"  ❌ COLLISION DETECTED: {total - unique_om109} duplicate fingerprints")
    cur.close()
    conn.close()

if __name__ == "__main__":
    run()
