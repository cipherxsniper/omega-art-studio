#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_v10.py", "r") as f:
    content = f.read()

# 1. Add import near top after existing imports
old_import = "import os, sys, json, time, signal, smtplib, imaplib, email as email_lib"
new_import = "import os, sys, json, time, signal, smtplib, imaplib, email as email_lib\ntry:\n    from omega_nft_webhook import handle_nft_checkout as _handle_nft_checkout\n    NFT_WEBHOOK_OK = True\nexcept Exception as _e:\n    NFT_WEBHOOK_OK = False\n    print(f'[omega_v10] NFT webhook not loaded: {_e}')"

if old_import not in content:
    print("ERROR: import line not found")
    raise SystemExit(1)

content = content.replace(old_import, new_import, 1)

# 2. Wire into _on_checkout_completed — add NFT check before B2B logic
old_checkout = "def _on_checkout_completed(data: dict):\n    email      = data.get(\"customer_email\") or data.get(\"customer_details\", {}).get(\"email\", \"\")\n    price_id   = \"\"\n    line_items = data.get(\"line_items\", {}).get(\"data\", [])\n    if line_items:\n        price_id = line_items[0].get(\"price\", {}).get(\"id\", \"\")\n    product_key = _resolve_product_key(price_id)"

new_checkout = """def _on_checkout_completed(data: dict):
    email      = data.get("customer_email") or data.get("customer_details", {}).get("email", "")
    price_id   = ""
    line_items = data.get("line_items", {}).get("data", [])
    if line_items:
        price_id = line_items[0].get("price", {}).get("id", "")

    # NFT purchase — check first before B2B logic
    if NFT_WEBHOOK_OK:
        try:
            nft_handled = _handle_nft_checkout(data)
            if nft_handled:
                notify(f"🎨 NFT SOLD — COA emailed to {email}")
                return
        except Exception as _nft_e:
            log("error", "nft_webhook", f"NFT handler failed: {_nft_e}")

    product_key = _resolve_product_key(price_id)"""

if old_checkout not in content:
    print("ERROR: checkout block not found")
    raise SystemExit(1)

content = content.replace(old_checkout, new_checkout, 1)

with open("/data/data/com.termux/files/home/omega_v10.py", "w") as f:
    f.write(content)
print("Patch applied")
