#!/usr/bin/env python3
"""
Omega Cloud Node 3 — HTTP Bridge
Connects Node 3 to Omega Bank + Omega Ledger
Exposes live bank and ledger activity via REST
"""
import json, os, hashlib, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
load_dotenv()

try:
    import psycopg2
    PG_OK = True
except ImportError:
    PG_OK = False

ADMIN_KEY = os.getenv('OMEGA_CLOUD_ADMIN_KEY', 'omega-admin')
PORT = 5010

def pg():
    return psycopg2.connect(
        host='127.0.0.1', port=5432,
        dbname='omega_bank', user='postgres',
        connect_timeout=5
    )

def auth(handler):
    token = handler.headers.get('Authorization','').replace('Bearer ','')
    return token == ADMIN_KEY

def respond(handler, code, data):
    body = json.dumps(data, default=str).encode()
    handler.send_response(code)
    handler.send_header('Content-Type','application/json')
    handler.send_header('Access-Control-Allow-Origin','*')
    handler.send_header('Content-Length', len(body))
    handler.end_headers()
    handler.wfile.write(body)

class OmegaBridge(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Headers','Authorization,Content-Type')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == '/health':
            respond(self, 200, {
                'status': 'online',
                'node': 'omega-node-003',
                'bridge': 'omega_bank',
                'time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            })
            return

        if not auth(self):
            respond(self, 401, {'error': 'unauthorized'}); return

        if path == '/v1/bank/wallets':
            if not PG_OK:
                respond(self, 503, {'error': 'psycopg2 not available'}); return
            try:
                conn = pg(); cur = conn.cursor()
                cur.execute("""
                    SELECT a.owner_name, a.account_type,
                           w.available_balance, w.settled_balance,
                           w.currency, w.status
                    FROM wallets w
                    JOIN accounts a ON a.account_id = w.account_id
                    ORDER BY w.available_balance DESC NULLS LAST
                """)
                rows = cur.fetchall()
                conn.close()
                respond(self, 200, {'wallets': [
                    {'name':r[0],'type':r[1],'available':float(r[2] or 0),
                     'settled':float(r[3] or 0),'currency':r[4],'status':r[5]}
                    for r in rows
                ]})
            except Exception as e:
                respond(self, 500, {'error': str(e)})

        elif path == '/v1/bank/ledger':
            if not PG_OK:
                respond(self, 503, {'error': 'psycopg2 not available'}); return
            try:
                conn = pg(); cur = conn.cursor()
                cur.execute("""
                    SELECT id, direction, amount, memo,
                           event_type, created_at,
                           LEFT(chain_hash,20),
                           LEFT(om109_fingerprint,20)
                    FROM ledger_entries
                    WHERE event_type NOT IN ('STRESS_TEST','STRESS_BILLION')
                    ORDER BY global_sequence DESC LIMIT 20
                """)
                rows = cur.fetchall()
                conn.close()
                respond(self, 200, {'entries': [
                    {'id':str(r[0]),'direction':r[1],
                     'amount':float(r[2] or 0),'memo':r[3],
                     'event_type':r[4],'created_at':str(r[5]),
                     'chain_hash':r[6],'om109':r[7]}
                    for r in rows
                ]})
            except Exception as e:
                respond(self, 500, {'error': str(e)})

        elif path == '/v1/bank/constitution':
            if not PG_OK:
                respond(self, 503, {'error': 'psycopg2 not available'}); return
            try:
                conn = pg(); cur = conn.cursor()
                cur.execute("""
                    SELECT invariant_name, description,
                           severity, enabled
                    FROM omega_constitution
                    ORDER BY severity, invariant_name
                """)
                rows = cur.fetchall()
                cur.execute("SELECT COUNT(*) FROM omega_invariant_violations")
                violations = cur.fetchone()[0]
                conn.close()
                respond(self, 200, {
                    'invariants': [
                        {'name':r[0],'description':r[1],
                         'severity':r[2],'enabled':r[3]}
                        for r in rows
                    ],
                    'total_violations': violations
                })
            except Exception as e:
                respond(self, 500, {'error': str(e)})

        elif path == '/v1/bank/violations':
            if not PG_OK:
                respond(self, 503, {'error': 'psycopg2 not available'}); return
            try:
                conn = pg(); cur = conn.cursor()
                cur.execute("""
                    SELECT v.id, c.invariant_name,
                           v.details, v.created_at
                    FROM omega_invariant_violations v
                    JOIN omega_constitution c ON c.id = v.invariant_id
                    ORDER BY v.created_at DESC LIMIT 10
                """)
                rows = cur.fetchall()
                conn.close()
                respond(self, 200, {'violations': [
                    {'id':str(r[0]),'invariant':r[1],
                     'details':r[2],'created_at':str(r[3])}
                    for r in rows
                ]})
            except Exception as e:
                respond(self, 500, {'error': str(e)})

        elif path == '/v1/bank/stats':
            if not PG_OK:
                respond(self, 503, {'error': 'psycopg2 not available'}); return
            try:
                conn = pg(); cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM ledger_entries WHERE event_type NOT IN ('STRESS_TEST','STRESS_BILLION')")
                entries = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM wallets")
                wallets = cur.fetchone()[0]
                cur.execute("SELECT SUM(available_balance) FROM wallets WHERE available_balance > 0")
                total_assets = cur.fetchone()[0] or 0
                cur.execute("SELECT COUNT(*) FROM omega_invariant_violations")
                violations = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM omega_constitution WHERE enabled=true")
                active_laws = cur.fetchone()[0]
                conn.close()
                respond(self, 200, {
                    'ledger_entries': entries,
                    'wallets': wallets,
                    'total_positive_assets': float(total_assets),
                    'constitutional_violations': violations,
                    'active_laws': active_laws,
                    'node': 'omega-node-003',
                    'dual_signing': 'SHA256 + OM109'
                })
            except Exception as e:
                respond(self, 500, {'error': str(e)})

        else:
            respond(self, 404, {'error': 'not found'})

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), OmegaBridge)
    print(f'Omega Node 3 Bridge — port {PORT}')
    print(f'Endpoints: /health /v1/bank/wallets /v1/bank/ledger')
    print(f'           /v1/bank/constitution /v1/bank/violations /v1/bank/stats')
    server.serve_forever()
