#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_provenance_api.py", "r") as f:
    content = f.read()

old = """                SELECT token_id, title, rarity, theme, image_sha256,
                       om109_fingerprint, om109_sig_a, om109_sig_b,
                       chain_hash, owner_account_id, is_founder_linked,
                       sale_status, minted_at, stripe_payment_link
                FROM nft_registry
                WHERE collection = %s
                ORDER BY token_id"""

new = """                SELECT token_id, title, rarity, theme, image_sha256,
                       om109_fingerprint, om109_sig_a, om109_sig_b,
                       chain_hash, owner_account_id, is_founder_linked,
                       sale_status, minted_at, stripe_payment_link
                FROM nft_registry
                WHERE collection = %s
                ORDER BY token_id ASC"""

# Find the actual query in get_collection
import re
pattern = r'(SELECT token_id.*?ORDER BY token_id)'
match = re.search(pattern, content, re.DOTALL)
if match:
    print(f"Found query: {match.group(0)[:80]}")
else:
    print("Query not found - showing get_collection section")
    idx = content.find('def get_collection')
    print(content[idx:idx+500])
