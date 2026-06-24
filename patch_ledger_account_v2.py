#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "r") as f:
    content = f.read()

old = '          "OMEGA_ART_STUDIO", buyer,'
new = '          "SYSTEM", buyer,'

if old not in content:
    print("ERROR: not found — showing ledger insert context")
    idx = content.find("NFT_SALE")
    print(repr(content[idx:idx+300]))
    raise SystemExit(1)

content = content.replace(old, new, 1)

with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "w") as f:
    f.write(content)
print("Patch applied")
