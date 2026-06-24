#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "r") as f:
    content = f.read()

# Use Thomas's real wallet UUID as debit_account for NFT sales
old = '          "OMEGA_ART_STUDIO", buyer,'
new = '          "2109a4cc-a066-4698-a478-a786bf096318", buyer,'

if old not in content:
    print("ERROR: account string not found")
    raise SystemExit(1)

content = content.replace(old, new, 1)

with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "w") as f:
    f.write(content)
print("Patch applied")
