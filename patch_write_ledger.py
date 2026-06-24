#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "r") as f:
    content = f.read()

old = '''def _write_ledger(conn, token, buyer, session_id):
    idem = hashlib.sha256(
        f"NFT_SALE:{token["collection"]}:{token["token_id"]}:{session_id}".encode()
    ).hexdigest()[:32]
    conn.execute("""
        INSERT INTO ledger_entries
            (idempotency_key, event_type, collection, token_id,
             from_account, to_account, amount_usd, stripe_session_id,
             om109_fingerprint, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
        ON CONFLICT (idempotency_key) DO NOTHING
    """, (idem, "NFT_SALE", token["collection"], token["token_id"],
          "OMEGA_ART_STUDIO", buyer, token.get("price_usd", 0),
          session_id, token.get("om109_fingerprint", "")))'''

new = '''def _write_ledger(conn, token, buyer, session_id):
    import uuid
    idem_key = hashlib.sha256(
        f"NFT_SALE:{token['collection']}:{token['token_id']}:{session_id}".encode()
    ).hexdigest()[:32]
    memo = (f"NFT_SALE: {token['collection']} #{token['token_id']} "
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
          "DEBIT"))'''

if old not in content:
    print("ERROR: _write_ledger not found")
    idx = content.find("def _write_ledger")
    print(repr(content[idx:idx+400]))
    raise SystemExit(1)

content = content.replace(old, new, 1)

with open("/data/data/com.termux/files/home/omega_nft_webhook.py", "w") as f:
    f.write(content)
print("Patch applied")
