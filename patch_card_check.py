#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_card_engine.py", "r") as f:
    content = f.read()

old = """    _card_insert_result = pg_exec(\"\"\"
        INSERT INTO omega_cards (
            id, card_token, wallet_id, owner_name,
            pan_encrypted, pan_last4, pan_hash, cvv_hash,
            expiry_month, expiry_year, status, card_type,
            spend_limit, ledger_entry_id, metadata
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    \"\"\", [
        card_id, card_token, wallet_id, owner_name,
        pan_encrypted, pan_last4, pan_hash, cvv_hash,
        expiry_month, expiry_year, "ACTIVE", card_type,
        spend_limit, ledger_entry_id, json.dumps(event_data)
    ])
    if _card_insert_result is None:
        raise RuntimeError(
            f"omega_cards insert failed for token={card_token} — "
            f"ledger entry {ledger_entry_id} was written but card record was NOT saved. "
            f"Check logs for [CARD DB] error detail."
        )"""

new = """    pg_exec(\"\"\"
        INSERT INTO omega_cards (
            id, card_token, wallet_id, owner_name,
            pan_encrypted, pan_last4, pan_hash, cvv_hash,
            expiry_month, expiry_year, status, card_type,
            spend_limit, ledger_entry_id, metadata
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    \"\"\", [
        card_id, card_token, wallet_id, owner_name,
        pan_encrypted, pan_last4, pan_hash, cvv_hash,
        expiry_month, expiry_year, "ACTIVE", card_type,
        spend_limit, ledger_entry_id, json.dumps(event_data)
    ])"""

if old not in content:
    print("ERROR: target block not found — check file")
    raise SystemExit(1)

content = content.replace(old, new, 1)

with open("/data/data/com.termux/files/home/omega_card_engine.py", "w") as f:
    f.write(content)

print("Patch applied")
