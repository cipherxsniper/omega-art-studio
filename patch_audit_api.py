import re

with open('/data/data/com.termux/files/home/omega_v10.py', 'r') as f:
    content = f.read()

AUDIT_ROUTES = '''
    @app.route("/audit/status", methods=["GET"])
    def audit_status():
        auth = flask_request.headers.get("Authorization", "")
        if auth != "Bearer " + os.getenv("OMEGA_AUDIT_TOKEN", "OMEGA2026"):
            return jsonify({"error": "unauthorized"}), 401
        return jsonify({
            "system": "Omega Bank",
            "status": "LIVE",
            "public_ip": "23.162.0.62",
            "ledger": "omega_bank",
            "auditor_role": "omega_auditor",
            "message": "SHA-256 hash-chained immutable ledger. Every entry signs the previous."
        })

    @app.route("/audit/ledger", methods=["GET"])
    def audit_ledger():
        auth = flask_request.headers.get("Authorization", "")
        if auth != "Bearer " + os.getenv("OMEGA_AUDIT_TOKEN", "OMEGA2026"):
            return jsonify({"error": "unauthorized"}), 401
        try:
            import psycopg2
            conn = psycopg2.connect(host="127.0.0.1", port=5432, user="omega_auditor",
                password="OmegaAudit2026!", dbname="omega_bank")
            cur = conn.cursor()
            offset = int(flask_request.args.get("offset", 0))
            limit = min(int(flask_request.args.get("limit", 100)), 500)
            cur.execute("SELECT id, created_at, amount, currency, entry_hash, global_sequence FROM ledger_entries ORDER BY global_sequence LIMIT %s OFFSET %s", (limit, offset))
            rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) FROM ledger_entries")
            total = cur.fetchone()[0]
            conn.close()
            return jsonify({
                "total_entries": total,
                "offset": offset,
                "limit": limit,
                "entries": [{"id": str(r[0]), "created_at": str(r[1]), "amount": str(r[2]),
                    "currency": r[3], "entry_hash": r[4], "global_sequence": r[5]} for r in rows]
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

'''

target = "    @app.route(\"/health\", methods=[\"GET\"])"
content = content.replace(target, AUDIT_ROUTES + target)

with open('/data/data/com.termux/files/home/omega_v10.py', 'w') as f:
    f.write(content)

print("PATCH APPLIED")
