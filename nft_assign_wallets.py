#!/usr/bin/env python3
"""
NFT Wallet Assignment — one-time deterministic population of nft_registry.
Matches the EXISTING nft_registry schema (owner_account_id, is_founder_linked, etc).
Mint history (JSONL + ledger_entries) remains untouched and immutable.
"""
import json, random, psycopg2
from pathlib import Path

LEDGER_LOG = Path("/data/data/com.termux/files/home/echoes_of_eternity/om109_ledger.jsonl")
DIAMOND_TOKEN_ID = 85
EXCLUDED_IDS = {101, 102, 103, 104, 105, 106}

WALLETS = [
    ("2109a4cc-a066-4698-a478-a786bf096318", "Thomas Lee Harvey — Omega Founder Wallet", True),
    ("a7889956-ca14-432a-9cb7-7dc17530b7d9", "Omega Merchant — NFT Holding", False),
    ("ed574d93-0abf-4cc5-b6e0-9d73b77da135", "OMEGA_CREDIT — NFT Holding", False),
    ("b702cb19-9b5c-44f4-8db4-161e3bf60655", "OMEGA_RESERVE_LEDGER — NFT Holding", False),
    ("0b608cb6-6745-4b75-bb9d-fa60e8a1b051", "OMEGA_SYSTEM_TREASURY — NFT Holding", False),
    ("4053d3a5-06b8-43d6-b8d5-5268991f8cbc", "OMEGA_GENESIS — NFT Holding", False),
    ("b4ab75f8-adc6-4981-ba48-d6dc3df423a5", "Omega Treasury Reserve — NFT Holding", False),
    ("fa4d0a6a-bb76-45ec-90f6-4ec37f847963", "Omega Investment Pool — NFT Holding", False),
    ("8ad07ed5-f433-4439-a188-f11b51110ae4", "Omega Credit Layer — NFT Holding", False),
    ("c182dbbc-e607-4364-a6cc-7611dac8eb95", "Omega Debit Layer — NFT Holding", False),
    ("fac22005-e8d3-4e08-ba89-c14150503429", "Omega Genesis Liquidity Origin — NFT Holding", False),
    ("cb8f4ebe-3205-408f-a765-148275ac36b8", "Reserve Ledger — NFT Holding", False),
    ("c8818380-c58d-4c52-a912-d69e0ae0d263", "Ops Float — NFT Holding", False),
]
assert len(WALLETS) == 13

entries_by_id = {}
with open(LEDGER_LOG) as f:
    for line in f:
        if not line.strip():
            continue
        e = json.loads(line)
        tid = e["token_id"]
        if tid not in entries_by_id:
            entries_by_id[tid] = e

rng = random.Random("OMEGA_GENESIS_THOMAS_LEE_HARVEY_OM109_2024_WALLET_ASSIGN")
candidate_pool = sorted(
    tid for tid in entries_by_id
    if tid != DIAMOND_TOKEN_ID and tid not in EXCLUDED_IDS and tid <= 100
)
chosen_12 = sorted(rng.sample(candidate_pool, 12))
assignments = [DIAMOND_TOKEN_ID] + chosen_12

print("Token assignments (deterministic):")
for tid, (wallet_id, owner_name, is_diamond) in zip(assignments, WALLETS):
    e = entries_by_id[tid]
    tag = " <-- IMPOSSIBLE DIAMOND" if is_diamond else ""
    print(f"  #{tid:04d} '{e['title']}' ({e['rarity']}) -> {owner_name}{tag}")

confirm = input("\nWrite these 13 assignments to EXISTING nft_registry? [y/N]: ").strip().lower()
if confirm != "y":
    print("Aborted — no changes made.")
    raise SystemExit(0)

conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="omega_ledger", user="postgres")
conn.autocommit = True
cur = conn.cursor()

inserted = 0
for tid, (wallet_id, owner_name, is_diamond) in zip(assignments, WALLETS):
    e = entries_by_id[tid]
    cur.execute("""
        INSERT INTO nft_registry
            (token_id, name, title, rarity, theme, image_sha256,
             om109_fingerprint, om109_sig_a, om109_sig_b, chain_hash,
             owner_account_id, is_founder_linked, minted_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (token_id) DO UPDATE SET
            owner_account_id = EXCLUDED.owner_account_id,
            is_founder_linked = EXCLUDED.is_founder_linked
    """, (
        tid, "Echoes of Eternity", e["title"], e["rarity"], e.get("theme",""),
        e["image_sha256"], e["om109_fingerprint"],
        e.get("sig_a",""), e.get("sig_b",""), e.get("chain_hash",""),
        wallet_id, is_diamond, e["minted_at"]
    ))
    inserted += 1
    print(f"  assigned #{tid:04d} -> {owner_name}")

conn.close()
print(f"\nDone. {inserted} tokens assigned across 13 wallets.")
