#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_provenance_api.py", "r") as f:
    content = f.read()

old = """            SELECT token_id, name, title, rarity, image_sha256, om109_fingerprint,
                   chain_hash, owner_account_id, collection, stripe_payment_link
            FROM nft_registry
            WHERE collection = %s
            ORDER BY token_id
        \"\"\", (col_name,))

        tokens = []
        for row in cur.fetchall():
            tokens.append({
                \"edition\": int(row[0]),
                \"token_id\": int(row[0]),
                \"name\": row[1] or \"\",
                \"title\": row[2] or \"\",
                \"rarity\": row[3] or \"Common\",
                \"image_sha256\": row[4] or \"\",
                \"om109_fingerprint\": row[5] or \"\",
                \"chain_hash\": row[6] or \"\",
                \"owner_account_id\": row[7] or \"\",
                \"collection\": row[8] or \"\",
                \"stripe_payment_link\": row[9] or \"\"
            })"""

new = """            SELECT token_id, title, rarity, theme, image_sha256, om109_fingerprint,
                   om109_sig_a, om109_sig_b, chain_hash, owner_account_id,
                   is_founder_linked, sale_status, minted_at, stripe_payment_link
            FROM nft_registry
            WHERE collection = %s
            ORDER BY token_id ASC
        \"\"\", (col_name,))

        tokens = []
        for row in cur.fetchall():
            tokens.append({
                \"token_id\": int(row[0]),
                \"title\": row[1] or \"\",
                \"rarity\": row[2] or \"Common\",
                \"theme\": row[3] or \"\",
                \"image_sha256\": row[4] or \"\",
                \"om109_fingerprint\": row[5] or \"\",
                \"om109_sig_a\": row[6] or \"\",
                \"om109_sig_b\": row[7] or \"\",
                \"chain_hash\": row[8] or \"\",
                \"owner_account_id\": row[9] or \"\",
                \"is_founder_linked\": bool(row[10]),
                \"sale_status\": row[11] or \"unsold\",
                \"minted_at\": str(row[12]) if row[12] else None,
                \"stripe_payment_link\": row[13] or \"\",
                \"collection\": col_name,
            })"""

if old not in content:
    print("ERROR: block not found")
    raise SystemExit(1)

content = content.replace(old, new, 1)

with open("/data/data/com.termux/files/home/omega_provenance_api.py", "w") as f:
    f.write(content)
print("Patch applied")
