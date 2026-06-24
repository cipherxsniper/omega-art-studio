#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "r") as f:
    lines = f.readlines()

start = None
end = None
for i, line in enumerate(lines):
    if "def _write_ledger(" in line:
        start = i
    if start and i > start and line.startswith("def "):
        end = i
        break

if start is None or end is None:
    print(f"ERROR: start={start} end={end}")
    raise SystemExit(1)

print(f"Replacing lines {start+1}-{end}")

new_func = '''def _write_ledger(conn, token, buyer, session_id):
    import uuid
    coll = token["collection"]
    tid = token["token_id"]
    idem_key = hashlib.sha256(
        f"NFT_SALE:{coll}:{tid}:{session_id}".encode()
    ).hexdigest()[:32]
    memo = (f"NFT_SALE: {coll} #{tid} "
            f"'{token.get('title','')}' -> {buyer} | session={session_id}")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ledger_entries
            (id, debit_account, credit_account, amount, memo,
             event_type, hash, direction)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO NOTHING
    """, (idem_key, "OMEGA_ART_STUDIO", buyer,
          token.get("price_usd", 0) or 0,
          memo, "NFT_SALE",
          token.get("om109_fingerprint", ""),
          "DEBIT"))

'''

lines[start:end] = [new_func]

with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "w") as f:
    f.writelines(lines)
print("Patch applied")
