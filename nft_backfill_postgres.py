#!/usr/bin/env python3
import json, hashlib, psycopg2

LEDGER_LOG = "/data/data/com.termux/files/home/echoes_of_eternity/om109_ledger.jsonl"
TARGET_IDS = set(range(1, 49))

conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="omega_bank", user="postgres")
conn.autocommit = True
cur = conn.cursor()

seen = set()
succeeded = []
skipped = []
failed = []

with open(LEDGER_LOG) as f:
    for line in f:
        if not line.strip():
            continue
        entry = json.loads(line)
        token_id = entry["token_id"]
        if token_id not in TARGET_IDS or token_id in seen:
            continue
        seen.add(token_id)

        image_hash = entry["image_sha256"]
        om109_fp   = entry["om109_fingerprint"]
        chain_hash = entry["chain_hash"]
        rarity     = entry["rarity"]
        title      = entry["title"]

        idem = hashlib.sha256(f"NFT_MINT:{token_id}:{image_hash}".encode()).hexdigest()[:32]
        memo = f"NFT #{token_id:04d} '{title}' {rarity} | SHA256:{image_hash[:16]}"

        try:
            cur.execute("""
                INSERT INTO ledger_entries
                    (transaction_id, wallet_id, event_type, amount, direction,
                     debit_account, credit_account, memo, idempotency_key,
                     om109_fingerprint, chain_hash)
                VALUES
                    (uuid_generate_v4(), '2db2e016-f6a1-4086-bec2-363edfb1c26b',
                     %s, 0.00, 'CREDIT', 'nft_collection', 'omega_treasury',
                     %s, %s, %s, %s)
                ON CONFLICT (idempotency_key) DO NOTHING
            """, (f"NFT_MINT_{rarity.upper().replace(' ','_')}", memo, idem, om109_fp, chain_hash))
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
print(f"\nSucceeded: {len(succeeded)} | Skipped (already minted): {len(skipped)} | Failed: {len(failed)}")
if failed:
    print("Failed tokens:", [f[0] for f in failed])
