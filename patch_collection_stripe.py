#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_provenance_api.py", "r") as f:
    content = f.read()

old = '                   chain_hash, owner_account_id, collection'
new = '                   chain_hash, owner_account_id, collection, stripe_payment_link'

if old not in content:
    print("ERROR: column list not found")
    raise SystemExit(1)

content = content.replace(old, new, 1)

# Also fix the row mapping to include stripe_payment_link
old2 = '                "collection": row[8] or ""'
new2 = '''                "collection": row[8] or "",
                    "stripe_payment_link": row[9] or ""'''

if old2 not in content:
    print("ERROR: row mapping not found")
    raise SystemExit(1)

content = content.replace(old2, new2, 1)

with open("/data/data/com.termux/files/home/omega_provenance_api.py", "w") as f:
    f.write(content)

print("Patch applied")
