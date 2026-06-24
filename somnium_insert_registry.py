#!/usr/bin/env python3
"""
Somnium — one-time insert of all 100 tokens into omega_ledger.nft_registry
Source of truth: ~/somnium/om109_ledger.jsonl (verified ALL CLEAN — 100 entries)
Safe to re-run: uses INSERT ... ON CONFLICT (collection, token_id) DO NOTHING
"""
import json
from pathlib import Path
import psycopg2

LEDGER = Path.home() / "somnium" / "om109_ledger.jsonl"
COLLECTION = "Somnium"
CREATOR = "Thomas Lee Harvey"

def main():
    entries = [json.loads(l) for l in open(LEDGER) if l.strip()]
    entries.sort(key=lambda e: e["token_id"])
    print(f"Read {len(entries)} entries from JSONL ledger")

    if len(entries) != 100:
        print(f"WARNING: expected 100, got {len(entries)} — STOPPING, review manually")
        return

    conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="omega_ledger",
                            user="postgres", connect_timeout=5)
    conn.autocommit = True
    cur = conn.cursor()

    inserted, skipped = 0, 0
    for e in entries:
        token_id = e["token_id"]
        title = e["title"]
        rarity = e["rarity"]
        theme = e.get("theme", "")
        image_hash = e["image_sha256"]
        om109_fp = e["om109_fingerprint"]
        sig_a = e["sig_a"]
        sig_b = e["sig_b"]
        chain_hash = e["chain_hash"]
        name = f"{COLLECTION} — Unique #{token_id:04d}" if rarity == "Impossible Diamond" else f"{COLLECTION} — {title} #{token_id:04d}"

        try:
            cur.execute("""
                INSERT INTO nft_registry
                    (token_id, name, title, rarity, theme, image_sha256,
                     om109_fingerprint, om109_sig_a, om109_sig_b, chain_hash,
                     owner_account_id, is_founder_linked, sale_status, collection)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (collection, token_id) DO NOTHING
            """, (token_id, name, title, rarity, theme, image_hash,
                  om109_fp, sig_a, sig_b, chain_hash,
                  "UNASSIGNED", False, "unsold", COLLECTION))
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as ex:
            print(f"  ERROR on token #{token_id:04d}: {ex}")
            conn.rollback()

    conn.close()
    print(f"\nInserted: {inserted} | Skipped (already present): {skipped}")

if __name__ == "__main__":
    main()
