#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_provenance_api.py", "r") as f:
    content = f.read()

# Find and replace the SELECT in get_collection
old = """                SELECT token_id, name, title, rarity, image_sha256, om109_fingerprint,
                       chain_hash, owner_account_id, collection
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

if old not in content:
    print("ERROR: query not found — showing actual text")
    idx = content.find("def get_collection")
    print(repr(content[idx:idx+600]))
    raise SystemExit(1)

content = content.replace(old, new, 1)

# Fix row mapping to match new columns
old_row = '''                tokens.append({
                    "token_id": r[0],
                    "title": r[1],
                    "rarity": r[2],
                    "theme": r[3],
                    "image_sha256": r[4],
                    "om109_fingerprint": r[5],
                    "om109_sig_a": r[6],
                    "om109_sig_b": r[7],
                    "chain_hash": r[8],
                    "owner_account_id": r[9],
                    "is_founder_linked": r[10],
                    "sale_status": r[11],
                    "minted_at": str(r[12]) if r[12] else None,
                    "stripe_payment_link": r[13],
                    "collection": col_name,
                })'''

new_row = '''                tokens.append({
                    "token_id": r[0],
                    "title": r[1],
                    "rarity": r[2],
                    "theme": r[3] or "",
                    "image_sha256": r[4] or "",
                    "om109_fingerprint": r[5] or "",
                    "om109_sig_a": r[6] or "",
                    "om109_sig_b": r[7] or "",
                    "chain_hash": r[8] or "",
                    "owner_account_id": r[9] or "",
                    "is_founder_linked": bool(r[10]),
                    "sale_status": r[11] or "unsold",
                    "minted_at": str(r[12]) if r[12] else None,
                    "stripe_payment_link": r[13] or "",
                    "collection": col_name,
                })'''

if old_row not in content:
    print("ERROR: row mapping not found — showing section")
    idx = content.find("tokens.append")
    print(repr(content[idx:idx+600]))
    raise SystemExit(1)

content = content.replace(old_row, new_row, 1)

with open("/data/data/com.termux/files/home/omega_provenance_api.py", "w") as f:
    f.write(content)

print("Patch applied")
