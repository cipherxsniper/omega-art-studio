#!/usr/bin/env python3
"""
Somnium — Postgres ledger backfill.
Writes all 100 mint events from the clean JSONL chain into omega_bank.ledger_entries.
Matches the exact write pattern from somnium_engine.py's ledger_mint_psql().
"""
import json, hashlib, psycopg2

LEDGER_LOG = "/data/data/com.termux/files/home/somnium/om109_ledger.jsonl"

conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="omega_bank", user="postgres")
conn.autocommit = True
cur = conn.cursor()

succeeded = []
skipped = []
failed = []

with open(LEDGER_LOG) as f:
    for line in f:
        if not line.strip():
            continue
        entry = json.loads(line)
        token_id   = entry["token_id"]
        image_hash = entry["image_sha256"]
        om109_fp   = entry["om109_fingerprint"]
        chain_hash = entry["chain_hash"]
        rarity     = entry["rarity"]
        title      = entry["title"]

        idem = hashlib.sha256(f"SOMNIUM_MINT:{token_id}:{image_hash}".encode()).hexdigest()[:32]
        memo = f"SOMNIUM #{token_id:04d} '{title}' {rarity} | SHA256:{image_hash[:16]}"

        try:
            cur.execute("""
                INSERT INTO ledger_entries
                    (transaction_id, wallet_id, event_type, amount, direction,
                     debit_account, credit_account, memo, idempotency_key,
                     om109_fingerprint, chain_hash)
                VALUES
                    (uuid_generate_v4(), '2db2e016-f6a1-4086-bec2-363edfb1c26b',
                     %s, 1.00, 'CREDIT', 'somnium_collection', 'omega_treasury',
                     %s, %s, %s, %s)
                ON CONFLICT (idempotency_key) DO NOTHING
            """, (f"SOMNIUM_MINT_{rarity.upper().replace(' ','_')}", memo, idem, om109_fp, chain_hash))
            succeeded.append(token_id)
            print(f"  OK   #{token_id:04d} — {title} ({rarity})")
        except psycopg2.errors.RaiseException as e:
            if "idempotency" in str(e).lower() or "duplicate" in str(e).lower():
                skipped.append(token_id)
                print(f"  SKIP #{token_id:04d} — already on ledger")
                conn.rollback()
            else:
                failed.append((token_id, str(e)[:80]))
                print(f"  FAIL #{token_id:04d} — {str(e)[:80]}")
                conn.rollback()
        except Exception as e:
            failed.append((token_id, str(e)[:80]))
            print(f"  FAIL #{token_id:04d} — {str(e)[:80]}")
            conn.rollback()

conn.close()
print(f"\nSucceeded: {len(succeeded)} | Skipped: {len(skipped)} | Failed: {len(failed)}")
if failed:
    print("Failed tokens:", [f[0] for f in failed])
