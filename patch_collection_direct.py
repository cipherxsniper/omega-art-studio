#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_provenance_api.py", "r") as f:
    content = f.read()

# Find start and end of get_collection method
start = content.find("    def get_collection(self, slug):")
end = content.find("    def get_wallet(self, wallet_id):")

if start == -1 or end == -1:
    print(f"ERROR: start={start} end={end}")
    raise SystemExit(1)

new_method = '''    def get_collection(self, slug):
        col_map = {
            "echoes": "Echoes of Eternity",
            "somnium": "Somnium",
            "paracosm": "Paracosm",
            "monolith": "Monolith"
        }
        col_name = col_map.get(slug, slug)
        try:
            conn = psycopg2.connect(PG_LEDGER)
            cur = conn.cursor()
            cur.execute("""
                SELECT token_id, title, rarity, theme, image_sha256,
                       om109_fingerprint, om109_sig_a, om109_sig_b,
                       chain_hash, owner_account_id, is_founder_linked,
                       sale_status, minted_at, stripe_payment_link
                FROM nft_registry
                WHERE collection = %s
                ORDER BY token_id ASC
            """, (col_name,))
            tokens = []
            for row in cur.fetchall():
                tokens.append({
                    "token_id": int(row[0]),
                    "title": row[1] or "",
                    "rarity": row[2] or "Common",
                    "theme": row[3] or "",
                    "image_sha256": row[4] or "",
                    "om109_fingerprint": row[5] or "",
                    "om109_sig_a": row[6] or "",
                    "om109_sig_b": row[7] or "",
                    "chain_hash": row[8] or "",
                    "owner_account_id": row[9] or "",
                    "is_founder_linked": bool(row[10]),
                    "sale_status": row[11] or "unsold",
                    "minted_at": str(row[12]) if row[12] else None,
                    "stripe_payment_link": row[13] or "",
                    "collection": col_name,
                })
            cur.close()
            conn.close()
            return {"collection": col_name, "count": len(tokens), "tokens": tokens}
        except Exception as e:
            return {"error": str(e)}

'''

content = content[:start] + new_method + content[end:]

with open("/data/data/com.termux/files/home/omega_provenance_api.py", "w") as f:
    f.write(content)
print("Patch applied")
