#!/usr/bin/env python3
import os, json
from datetime import datetime
from flask import Flask, jsonify, request

try:
    import psycopg2, psycopg2.extras
    HAVE_PG = True
except ImportError:
    HAVE_PG = False

DB_HOST = os.getenv("OMEGA_DB_HOST", "192.168.11.2")
DB_PORT = int(os.getenv("OMEGA_DB_PORT", "5432"))
DB_NAME = os.getenv("OMEGA_DB_NAME", "omega")
DB_USER = os.getenv("OMEGA_DB_USER", "omega")
DB_PASS = os.getenv("OMEGA_DB_PASS", "omega")

app = Flask(__name__)

def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS, connect_timeout=5,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )

@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    return r

@app.route("/health")
def health():
    try:
        c = get_conn(); c.cursor().execute("SELECT 1"); c.close()
        return jsonify({"status":"ok","db":"connected"})
    except Exception as e:
        return jsonify({"status":"error","db":str(e)}), 500

@app.route("/stats")
def stats():
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM ledger_entries")
        tx = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(DISTINCT account_id) AS n FROM accounts")
        wc = cur.fetchone()["n"]
        oracle = None
        try:
            cur.execute("SELECT score FROM oracle_scores ORDER BY recorded_at DESC LIMIT 1")
            r = cur.fetchone(); oracle = float(r["score"]) if r else None
        except: conn.rollback()
        height = 0
        try:
            cur.execute("SELECT MAX(sequence_no) AS h FROM ledger_entries")
            r = cur.fetchone(); height = r["h"] or 0
        except: conn.rollback()
        nfts = 400
        try:
            cur.execute("SELECT COUNT(*) AS n FROM nft_tokens")
            nfts = cur.fetchone()["n"]
        except: conn.rollback()
        cur.close(); conn.close()
        return jsonify({"tx_count":tx,"wallet_count":wc,"oracle_score":oracle,
            "block_height":height,"nft_count":nfts,
            "timestamp":datetime.utcnow().isoformat()+"Z",
            "nodes":[{"ip":"192.168.11.115","role":"control","status":"online"},
                     {"ip":"192.168.11.2","role":"postgres","status":"online"}]})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/wallets")
def wallets():
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            SELECT a.account_id AS addr, a.account_name AS label, a.account_type AS tag,
                COALESCE(
                    (SELECT SUM(amount) FROM ledger_entries WHERE account_id=a.account_id AND entry_type='CREDIT')
                   -(SELECT COALESCE(SUM(amount),0) FROM ledger_entries WHERE account_id=a.account_id AND entry_type='DEBIT'),
                0) AS balance
            FROM accounts a ORDER BY balance DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        for w in rows: w["balance"] = float(w["balance"])
        total = sum(w["balance"] for w in rows)
        for w in rows: w["share"] = round(w["balance"]/total*100,2) if total else 0
        return jsonify({"wallets":rows,"total_supply":total,"count":len(rows)})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/verify")
def verify():
    q = request.args.get("q","").strip()
    if not q: return jsonify({"error":"q required"}), 400
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            SELECT token_id, collection, title, fingerprint,
                   minted_at, owner_address AS owner, tx_hash
            FROM nft_tokens
            WHERE token_id=%s OR fingerprint=%s OR LOWER(title)=LOWER(%s)
            LIMIT 1
        """, (q,q,q))
        row = cur.fetchone(); cur.close(); conn.close()
        if row:
            d = dict(row); d["authentic"] = True
            if d.get("minted_at"): d["minted_at"] = str(d["minted_at"])
            return jsonify(d)
        return jsonify({"authentic":False,"query":q})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/transactions")
def transactions():
    limit = min(int(request.args.get("limit",20)),100)
    offset = int(request.args.get("offset",0))
    try:
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            SELECT le.sequence_no, le.account_id, a.account_name,
                   le.entry_type, le.amount, le.currency,
                   le.description, le.tx_hash, le.created_at
            FROM ledger_entries le
            LEFT JOIN accounts a ON a.account_id=le.account_id
            ORDER BY le.sequence_no DESC LIMIT %s OFFSET %s
        """, (limit, offset))
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            if d.get("amount"): d["amount"] = float(d["amount"])
            if d.get("created_at"): d["created_at"] = str(d["created_at"])
            rows.append(d)
        cur.close(); conn.close()
        return jsonify({"transactions":rows})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

if __name__ == "__main__":
    print(f"Omega API → http://0.0.0.0:8082  |  DB: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    app.run(host="0.0.0.0", port=8082, debug=False)
