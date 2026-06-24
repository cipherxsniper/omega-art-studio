#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "r") as f:
    content = f.read()

old = '            cur.execute("UPDATE nft_registry SET sale_status=%s, owner_account_id=%s, sold_at=NOW() WHERE collection=%s AND token_id=%s AND sale_status!=%s",\n                           ("sold", buyer, coll, tid, "sold"))'

new = '''            receipt_hash = hashlib.sha256(
                f"RECEIPT:{coll}:{tid}:{session_id}".encode()
            ).hexdigest()[:16]
            cur.execute("""UPDATE nft_registry
                SET sale_status=%s, owner_account_id=%s,
                    sold_at=NOW(), receipt_hash=%s
                WHERE collection=%s AND token_id=%s
                AND sale_status!=%s""",
                ("sold", buyer, receipt_hash, coll, tid, "sold"))'''

if old not in content:
    print("ERROR: UPDATE not found — showing context")
    idx = content.find("UPDATE nft_registry")
    print(repr(content[idx-50:idx+200]))
    raise SystemExit(1)

content = content.replace(old, new, 1)

# Remove duplicate receipt_hash generation below
old_dup = '''            receipt_hash = hashlib.sha256(
                f"RECEIPT:{coll}:{tid}:{session_id}".encode()
            ).hexdigest()[:16]
            passport_url = _live_passport_url(buyer) if buyer != "unknown" else ""'''

new_dup = '            passport_url = _live_passport_url(buyer) if buyer != "unknown" else ""'

if old_dup in content:
    content = content.replace(old_dup, new_dup, 1)
    print("Removed duplicate receipt_hash generation")

with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "w") as f:
    f.write(content)
print("Patch applied")
