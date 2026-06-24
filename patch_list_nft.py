path = "/data/data/com.termux/files/home/omega_marketplace.py"
with open(path) as f:
    lines = f.readlines()

# 1-indexed lines 83-90 -> 0-indexed 82:90
start = 82
end = 90

removed = lines[start:end]
print("REMOVING:")
print("".join(removed))

new_block = '''        # Log to audit_log (non-transfer event, not a ledger movement)
        entry_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO audit_log (id, actor, action, entity_type, entity_id, details)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (entry_id, seller_wallet, 'NFT_LISTED', 'nft_listing', str(listing_id),
              json.dumps({"token_id": token_id, "starting_price_omg": float(starting_price_omg)})))
'''

lines[start:end] = [new_block]

with open(path, "w") as f:
    f.writelines(lines)

print("PATCH APPLIED SUCCESSFULLY")
