#!/usr/bin/env python3
"""Patch: add UUID bridge map and fix get_wallet balance lookup"""
import re

with open("/data/data/com.termux/files/home/omega_provenance_api.py", "r") as f:
    content = f.read()

# Add bridge map after NFT_WALLET_MAP closing brace
bridge_map = '''
# Bridge: NFT wallet UUID -> Banking wallet UUID (for balance lookup)
NFT_TO_BANK_UUID = {
    "2109a4cc-a066-4698-a478-a786bf096318": "7597e069-65bc-4b55-b420-a2a2682f53e0",
    "a7889956-ca14-432a-9cb7-7dc17530b7d9": "8fcaf9c3-24d1-4c4b-ad88-856576b8b6e9",
    "ed574d93-0abf-4cc5-b6e0-9d73b77da135": "70e8cdae-983c-4392-a97a-4ae06217b303",
    "b702cb19-9b5c-44f4-8db4-161e3bf60655": "fe881e17-8b24-42f4-ba4f-c1ce38770b51",
    "0b608cb6-6745-4b75-bb9d-fa60e8a1b051": "92f17408-e801-4e89-8494-d8c414fa1ca7",
    "4053d3a5-06b8-43d6-b8d5-5268991f8cbc": "19841a36-3d95-46ab-a154-99684fefd57e",
    "b4ab75f8-adc6-4981-ba48-d6dc3df423a5": "80795b24-da42-4b9f-aa32-0349004880dc",
    "fa4d0a6a-bb76-45ec-90f6-4ec37f847963": "8a06f132-50d3-49c5-881f-795f951af503",
    "8ad07ed5-f433-4439-a188-f11b51110ae4": "0018b87b-1daf-472c-b8c8-eff8cb9aa198",
    "c182dbbc-e607-4364-a6cc-7611dac8eb95": "a2a76886-1222-4ae9-bd0c-939b509ec755",
    "fac22005-e8d3-4e08-ba89-c14150503429": "708f2b6b-094b-4898-8368-e27dfeac1a2f",
    "cb8f4ebe-3205-408f-a765-148275ac36b8": "2db2e016-f6a1-4086-bec2-363edfb1c26b",
    "c8818380-c58d-4c52-a912-d69e0ae0d263": "2ac05c75-c429-4550-b7c9-1a9bce3a17e7",
}
'''

# Insert bridge map after NFT_WALLET_MAP block
old = '"c8818380-c58d-4c52-a912-d69e0ae0d263": "Ops Float",\n}'
new = '"c8818380-c58d-4c52-a912-d69e0ae0d263": "Ops Float",\n}' + bridge_map

if old not in content:
    print("ERROR: could not find NFT_WALLET_MAP closing brace — check file")
    raise SystemExit(1)

content = content.replace(old, new, 1)

# Fix get_wallet: use bank UUID for balance lookup
old_balance = '        cur.execute("SELECT available_balance FROM wallets WHERE account_id = %s", (wallet_id,))'
new_balance = '''        bank_uuid = NFT_TO_BANK_UUID.get(wallet_id, wallet_id)
        cur.execute("SELECT settled_balance FROM wallets WHERE id = %s", (bank_uuid,))'''

if old_balance not in content:
    print("ERROR: could not find balance query line — check file")
    raise SystemExit(1)

content = content.replace(old_balance, new_balance, 1)

with open("/data/data/com.termux/files/home/omega_provenance_api.py", "w") as f:
    f.write(content)

print("Patch applied successfully")
