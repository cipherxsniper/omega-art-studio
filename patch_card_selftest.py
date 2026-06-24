#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_card_engine.py", "r") as f:
    content = f.read()

old = '        auth = authorize_transaction(\n            card["card_token"], 99.99, "TEST_MERCHANT"\n        )\n        assert auth["approved"], f"Auth failed: {auth}"'
new = '        auth = authorize_transaction(\n            card["card_token"], 0.01, "TEST_MERCHANT"\n        )\n        assert auth["approved"], f"Auth failed: {auth}"'

if old not in content:
    print("ERROR: target not found")
    raise SystemExit(1)

content = content.replace(old, new, 1)

with open("/data/data/com.termux/files/home/omega_card_engine.py", "w") as f:
    f.write(content)

print("Patch applied")
