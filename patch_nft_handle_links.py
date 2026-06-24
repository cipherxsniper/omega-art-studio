#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "r") as f:
    content = f.read()

old = '            if buyer != "unknown":\n                _send_coa_email(token, buyer, image_path, receipt_hash, passport_url)'

new = '''            receipt_hash = hashlib.sha256(
                f"RECEIPT:{coll}:{tid}:{session_id}".encode()
            ).hexdigest()[:16]
            passport_url = _live_passport_url(buyer) if buyer != "unknown" else ""
            if buyer != "unknown":
                _send_coa_email(token, buyer, image_path, receipt_hash, passport_url)'''

if old not in content:
    print("ERROR: send call not found — showing context")
    idx = content.find("_send_coa_email")
    print(repr(content[idx-200:idx+100]))
    raise SystemExit(1)

content = content.replace(old, new, 1)

with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "w") as f:
    f.write(content)
print("Patch applied")
