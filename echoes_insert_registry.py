#!/usr/bin/env python3
import json
from pathlib import Path
import psycopg2

LEDGER     = Path.home() / "echoes_of_eternity" / "om109_ledger.jsonl"
COLLECTION = "Echoes of Eternity"

def main():
    entries = [json.loads(l) for l in open(LEDGER) if l.strip()]
    entries.sort(key=lambda e: e["token_id"])
    print(f"Read {len(entries)} entries")

    conn = psycopg2.connect(host="127.0.0.1", port=5432,
                            dbname="omega_ledger", user="postgres", connect_timeout=5)
    conn.autocommit = True
    cur = conn.cursor()

    inserted = skipped = 0
    for e in entries:
        tid   = e["token_id"]
        title = e["title"]
        rarity = e["rarity"]
        name  = f"{COLLECTION} — Unique #{tid:04d}" if rarity == "Impossible Diamond" \
                else f"{COLLECTION} — {title} #{tid:04d}"
        try:
            cur.execute("""
                INSERT INTO nft_registry
                    (token_id, name, title, rarity, theme, image_sha256,
                     om109_fingerprint, om109_sig_a, om109_sig_b, chain_hash,
                     owner_account_id, is_founder_linked, sale_status, collection)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (collection, token_id) DO NOTHING
            """, (tid, name, title, rarity, e.get("theme",""),
                  e["image_sha256"], e["om109_fingerprint"],
                  e["sig_a"], e["sig_b"], e["chain_hash"],
                  "UNASSIGNED", False, "unsold", COLLECTION))
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as ex:
            print(f"  ERROR #{tid:04d}: {ex}")
            conn.rollback()

    conn.close()
    print(f"Inserted: {inserted} | Skipped: {skipped}")

if __name__ == "__main__":
    main()
