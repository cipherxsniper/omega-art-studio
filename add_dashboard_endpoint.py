PATH = "/data/data/com.termux/files/home/omega_v10.py"
with open(PATH) as f:
    src = f.read()

NEW_ROUTE = '''
    @app.route("/dashboard-data", methods=["GET"])
    def dashboard_data():
        try:
            import psycopg2
            pg = psycopg2.connect(
                host="127.0.0.1", port=5432,
                dbname="omega_bank", user="postgres",
                connect_timeout=3
            )
            cur = pg.cursor()
            cur.execute("SELECT COUNT(*) FROM ledger_entries")
            ledger_count = cur.fetchone()[0]
            cur.execute("""
                SELECT a.owner_name, w.available_balance
                FROM wallets w
                JOIN accounts a ON a.account_id = w.account_id
                ORDER BY w.available_balance DESC NULLS LAST
                LIMIT 6
            """)
            wallets = [{"name": r[0], "balance": float(r[1] or 0)}
                      for r in cur.fetchall()]
            cur.execute(
                "SELECT COUNT(*) FROM ledger_entries "
                "WHERE om109_fingerprint IS NOT NULL"
            )
            om109_count = cur.fetchone()[0]
            pg.close()
        except Exception:
            ledger_count = om109_count = 0
            wallets = []

        try:
            import sqlite3 as _sq
            db = _sq.connect(str(DB_PATH))
            c = db.cursor()
            emails_sent  = c.execute("SELECT COUNT(*) FROM emails_sent").fetchone()[0]
            leads_ready  = c.execute("SELECT COUNT(*) FROM leads WHERE status=\\'new\\'").fetchone()[0]
            interested   = c.execute("SELECT COUNT(*) FROM leads WHERE status=\\'interested\\'").fetchone()[0]
            sent_today   = c.execute("SELECT COUNT(*) FROM emails_sent WHERE date(sent_at)=date(\\'now\\')").fetchone()[0]
            clients      = [{"name": r[0], "status": r[1], "mrr": r[2]}
                           for r in c.execute("SELECT name, status, mrr FROM clients").fetchall()]
            db.close()
        except Exception:
            emails_sent = leads_ready = interested = sent_today = 0
            clients = []

        try:
            import json as _j
            hist = _j.loads(open("/data/data/com.termux/files/home/omega_oracle_history.json").read())
            latest = hist[-1] if hist else {}
            oracle_score = latest.get("total", 0)
            oracle_patch = latest.get("patch_count", 0)
            oracle_hash  = latest.get("system_hash", "")
        except Exception:
            oracle_score = oracle_patch = 0
            oracle_hash = ""

        return jsonify({
            "ledger_entries": ledger_count,
            "om109_signed":   om109_count,
            "wallets":        wallets,
            "emails_sent":    emails_sent,
            "sent_today":     sent_today,
            "leads_ready":    leads_ready,
            "interested":     interested,
            "clients":        clients,
            "oracle_score":   oracle_score,
            "oracle_patch":   oracle_patch,
            "oracle_hash":    oracle_hash,
            "nodes":          3,
            "status":         "ONLINE"
        })

'''

OLD = '    @app.route("/health", methods=["GET"])'
if OLD in src:
    src = src.replace(OLD, NEW_ROUTE + OLD, 1)
    print("✅ Dashboard endpoint added")
else:
    print("❌ NOT FOUND")

with open(PATH, "w") as f:
    f.write(src)
