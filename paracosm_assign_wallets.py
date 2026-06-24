#!/usr/bin/env python3
"""Paracosm — deterministic founder wallet assignment"""
import json, random
import psycopg2

GENESIS_SEED  = "OMEGA_GENESIS_THOMAS_LEE_HARVEY_PARACOSM_2026"
WALLET_SEED   = "OMEGA_PARACOSM_WALLET_ASSIGN_2026"
THOMAS_WALLET = "2109a4cc-a066-4698-a478-a786bf096318"
TOKEN_OFFSET  = 1000
TOTAL_SUPPLY  = 100
COLLECTION    = "Paracosm"

_imp_rng = random.Random(GENESIS_SEED + "_IMPOSSIBLE")
IMPOSSIBLE_TOKENS = sorted(_imp_rng.sample(range(TOKEN_OFFSET+1, TOKEN_OFFSET+101), 5))

FOUNDER_WALLETS = [
    ("2109a4cc-a066-4698-a478-a786bf096318", "Thomas Lee Harvey — Omega Founder Wallet"),
    ("a7889956-ca14-432a-9cb7-7dc17530b7d9", "Omega Merchant — NFT Holding"),
    ("ed574d93-0abf-4cc5-b6e0-9d73b77da135", "OMEGA_CREDIT — NFT Holding"),
    ("b702cb19-9b5c-44f4-8db4-161e3bf60655", "OMEGA_RESERVE_LEDGER — NFT Holding"),
    ("0b608cb6-6745-4b75-bb9d-fa60e8a1b051", "OMEGA_SYSTEM_TREASURY — NFT Holding"),
    ("4053d3a5-06b8-43d6-b8d5-5268991f8cbc", "OMEGA_GENESIS — NFT Holding"),
    ("b4ab75f8-adc6-4981-ba48-d6dc3df423a5", "Omega Treasury Reserve — NFT Holding"),
    ("fa4d0a6a-bb76-45ec-90f6-4ec37f847963", "Omega Investment Pool — NFT Holding"),
    ("8ad07ed5-f433-4439-a188-f11b51110ae4", "Omega Credit Layer — NFT Holding"),
    ("c182dbbc-e607-4364-a6cc-7611dac8eb95", "Omega Debit Layer — NFT Holding"),
    ("fac22005-e8d3-4e08-ba89-c14150503429", "Omega Genesis Liquidity Origin — NFT Holding"),
    ("cb8f4ebe-3205-408f-a765-148275ac36b8", "Reserve Ledger — NFT Holding"),
    ("c8818380-c58d-4c52-a912-d69e0ae0d263", "Ops Float — NFT Holding"),
]

def compute_assignments():
    rng = random.Random(WALLET_SEED)
    thomas_token = IMPOSSIBLE_TOKENS[0]
    other_diamonds = IMPOSSIBLE_TOKENS[1:]
    non_diamond_pool = [t for t in range(TOKEN_OFFSET+1, TOKEN_OFFSET+TOTAL_SUPPLY+1)
                        if t not in IMPOSSIBLE_TOKENS]
    founder_tokens_12 = rng.sample(non_diamond_pool, 12)
    assignments = {}
    assignments[thomas_token] = (THOMAS_WALLET, "Thomas Lee Harvey — Omega Founder Wallet", True)
    other_founders = [w for w in FOUNDER_WALLETS if w[0] != THOMAS_WALLET]
    for (wallet_id, name), token_id in zip(other_founders, founder_tokens_12):
        assignments[token_id] = (wallet_id, name, False)
    print(f"  Thomas Lee Harvey holds Impossible Diamond: #{thomas_token:04d}")
    print(f"  Other 4 Impossible Diamonds (unassigned): {[f'#{t:04d}' for t in other_diamonds]}")
    return assignments, other_diamonds

def main():
    assignments, free_diamonds = compute_assignments()
    print(f"\nToken assignments (deterministic):")
    for token_id in sorted(assignments.keys()):
        wallet_id, name, is_founder = assignments[token_id]
        imp = " ★ IMPOSSIBLE DIAMOND" if token_id in IMPOSSIBLE_TOKENS else ""
        print(f"  #{token_id:04d} -> {name}{imp}")

    ans = input("\nWrite to omega_ledger.nft_registry (Paracosm)? [y/N]: ")
    if ans.lower() != "y":
        print("Aborted."); return

    conn = psycopg2.connect(host="127.0.0.1", port=5432,
                            dbname="omega_ledger", user="postgres", connect_timeout=5)
    conn.autocommit = True
    cur = conn.cursor()

    for token_id, (wallet_id, name, is_founder) in assignments.items():
        cur.execute("""
            UPDATE nft_registry
            SET owner_account_id = %s,
                is_founder_linked = %s,
                sale_status = 'founder_held'
            WHERE token_id = %s AND collection = %s
        """, (wallet_id, is_founder, token_id, COLLECTION))
        print(f"  assigned #{token_id:04d} -> {name}")

    conn.close()
    print(f"\nDone. {len(assignments)} tokens assigned.")
    print(f"4 Impossible Diamonds remain unassigned: {[f'#{t:04d}' for t in free_diamonds]}")

if __name__ == "__main__":
    main()
