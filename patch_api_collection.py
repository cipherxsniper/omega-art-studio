#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_provenance_api.py", "r") as f:
    content = f.read()

# Add route
old = '            elif path == "/ledger/stats":'
new = '''            elif path.startswith("/collection/"):
                slug = path.split("/collection/")[1].strip("/")
                self.json_response(self.get_collection(slug))
            elif path == "/ledger/stats":'''

if old not in content:
    print("ERROR: route anchor not found")
    raise SystemExit(1)

content = content.replace(old, new, 1)

# Add method before get_ledger_stats
old = '    def get_ledger_stats(self):'
new = '''    def get_collection(self, slug):
        """Return all tokens for a collection in one query."""
        col_map = {
            "echoes": "Echoes of Eternity",
            "somnium": "Somnium",
            "paracosm": "Paracosm",
            "monolith": "Monolith",
        }
        col_name = col_map.get(slug)
        if not col_name:
            return {"error": f"Unknown collection: {slug}"}
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
                ORDER BY token_id
            """, (col_name,))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            tokens = []
            for r in rows:
                tokens.append({
                    "token_id": r[0],
                    "title": r[1],
                    "rarity": r[2],
                    "theme": r[3],
                    "image_sha256": r[4],
                    "om109_fingerprint": r[5],
                    "om109_sig_a": r[6],
                    "om109_sig_b": r[7],
                    "chain_hash": r[8],
                    "owner_account_id": r[9],
                    "is_founder_linked": r[10],
                    "sale_status": r[11],
                    "minted_at": str(r[12]) if r[12] else None,
                    "stripe_payment_link": r[13],
                    "collection": col_name,
                })
            return {"collection": col_name, "count": len(tokens), "tokens": tokens}
        except Exception as e:
            return {"error": str(e)}

    def get_ledger_stats(self):'''

if '    def get_ledger_stats(self):' not in content:
    print("ERROR: get_ledger_stats not found")
    raise SystemExit(1)

content = content.replace('    def get_ledger_stats(self):', new, 1)

with open("/data/data/com.termux/files/home/omega_provenance_api.py", "w") as f:
    f.write(content)

print("Patch applied")
