path = "/data/data/com.termux/files/home/omega_marketplace.py"
with open(path) as f:
    lines = f.readlines()

# Lines 37-43 (1-indexed) -> indices 36-42 (0-indexed), replace inclusive
start = 36
end = 43  # exclusive, i.e. up to and including 1-indexed line 43

removed = lines[start:end]
print("REMOVING:")
print("".join(removed))

new_block = '''        # Log to ledger as TWO rows: a DEBIT and a CREDIT (true double-entry)
        debit_id = str(uuid.uuid4())
        credit_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO ledger_entries
            (id, debit_account, credit_account, amount, memo, event_type, direction, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (debit_id, from_wallet, to_wallet, amount, reason, 'TOKEN_TRANSFER', 'DEBIT'))
        cur.execute("""
            INSERT INTO ledger_entries
            (id, debit_account, credit_account, amount, memo, event_type, direction, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (credit_id, from_wallet, to_wallet, amount, reason, 'TOKEN_TRANSFER', 'CREDIT'))
'''

lines[start:end] = [new_block]

with open(path, "w") as f:
    f.writelines(lines)

print("PATCH APPLIED SUCCESSFULLY")
