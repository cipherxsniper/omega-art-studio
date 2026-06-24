#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "r") as f:
    content = f.read()

# 1. Add receipt + passport links to email body
old_body = 'Verify: {_live_verify_url(token["collection"], tid)}\n\n"{quote}"\n\nThomas Lee Harvey\nCEO & Founder, Omega Art Studio\n"""'

new_body = '''Verify: {_live_verify_url(token["collection"], tid)}
{("\\nReceipt : " + _live_receipt_url(receipt_hash)) if receipt_hash else ""}
{("\\nCollector Passport : " + passport_url) if passport_url else ""}

"{quote}"

Thomas Lee Harvey
CEO & Founder, Omega Art Studio
"""'''

if old_body not in content:
    print("ERROR: body not found")
    raise SystemExit(1)

content = content.replace(old_body, new_body, 1)

# 2. Generate receipt_hash and passport_url in handle_nft_checkout before _send_coa_email
old_send = '            if buyer != "unknown":\n                _send_coa_email(token, buyer, image_path, receipt_hash, passport_url)'

new_send = '''            receipt_hash = hashlib.sha256(
                f"RECEIPT:{coll}:{tid}:{session_id}".encode()
            ).hexdigest()[:16]
            passport_url = _live_passport_url(buyer) if buyer != "unknown" else ""
            if buyer != "unknown":
                _send_coa_email(token, buyer, image_path, receipt_hash, passport_url)'''

if old_send not in content:
    print("ERROR: send call not found")
    raise SystemExit(1)

content = content.replace(old_send, new_send, 1)

with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "w") as f:
    f.write(content)
print("Patch applied")
