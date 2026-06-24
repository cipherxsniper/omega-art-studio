#!/usr/bin/env python3
"""
OMEGA SUGGESTION ENGINE
"""

import os
import json
import psycopg2
import subprocess
import sys
import requests
from datetime import datetime, timedelta

PG_BANK = "dbname=omega_bank user=postgres host=127.0.0.1 port=5432"
PG_LEDGER = "dbname=omega_ledger user=postgres host=127.0.0.1 port=5432"
CLAUDE_MODEL = "claude-sonnet-4-6"
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

def get_env_var(key):
    """Read from .env file"""
    try:
        with open(os.path.expanduser('~/.env')) as f:
            for line in f:
                if line.startswith(f'{key}='):
                    return line.split('=', 1)[1].strip()
    except:
        pass
    return None

def gather_state():
    state = {
        'timestamp': datetime.now().isoformat(),
        'oracle': get_oracle_grade(),
        'health': get_service_health(),
        'sales': get_nft_sales_trend(),
        'wallets': get_wallet_summary(),
        'ledger': get_ledger_health(),
    }
    return state

def get_oracle_grade():
    try:
        result = subprocess.run(['python3', '/home/omega/omega_oracle_v3.py'],
                              capture_output=True, text=True, timeout=15)
        for line in (result.stdout + result.stderr).split('\n'):
            if 'Grade:' in line:
                return line.split('Grade:')[1].strip().split()[0]
    except:
        pass
    return 'N/A'

def get_service_health():
    services = {
        'oracle': 'omega_v10.py',
        'sentinel': 'omega_sentinel.py',
        'provenance_api': 'omega_provenance_api.py',
        'gallery_server': 'omega_gallery_server.py'
    }
    health = {}
    for name, pattern in services.items():
        result = subprocess.run(['pgrep', '-f', pattern], capture_output=True)
        health[name] = 'UP' if result.returncode == 0 else 'DOWN'
    return health

def get_nft_sales_trend():
    try:
        conn = psycopg2.connect(PG_LEDGER)
        cur = conn.cursor()
        cur.execute("""
            SELECT DATE(sold_at), COUNT(*) as count, SUM(price_usd) as revenue
            FROM nft_registry
            WHERE sold_at >= NOW() - INTERVAL '7 days'
            AND sale_status = 'sold'
            GROUP BY DATE(sold_at)
            ORDER BY DATE(sold_at) DESC
        """)
        data = [{'date': str(row[0]), 'count': row[1], 'revenue': float(row[2] or 0)} for row in cur.fetchall()]
        cur.close()
        conn.close()
        return data
    except:
        return []

def get_wallet_summary():
    try:
        conn = psycopg2.connect(PG_BANK)
        cur = conn.cursor()
        cur.execute("SELECT SUM(available_balance), COUNT(*) FROM wallets")
        total, count = cur.fetchone()
        cur.close()
        conn.close()
        return {'total': float(total or 0), 'count': count}
    except:
        return {}

def get_ledger_health():
    try:
        conn = psycopg2.connect(PG_LEDGER)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ledger_entries")
        total_entries = cur.fetchone()[0]
        cur.close()
        conn.close()
        return {'total': total_entries}
    except:
        return {}

def get_claude_suggestion(state):
    """Send state to Claude, get back structured suggestions"""
    api_key = get_env_var('ANTHROPIC_API_KEY')
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY not in ~/.env")
        return None
    
    prompt = f"""You are the Omega system's AI advisor. Analyze this state and suggest ONE actionable fix.

STATE:
{json.dumps(state, indent=2)}

RESPOND WITH ONLY THIS JSON:
{{
  "suggestion": "action name",
  "description": "what to do and why",
  "category": "auto_approve|manual_review|escalate",
  "risk": "LOW|MEDIUM|HIGH",
  "time_estimate": "30s|5m|30m"
}}
"""

    headers = {
        'x-api-key': api_key,
        'content-type': 'application/json',
        'anthropic-version': '2023-06-01'
    }
    
    payload = {
        'model': CLAUDE_MODEL,
        'max_tokens': 500,
        'messages': [{'role': 'user', 'content': prompt}]
    }
    
    try:
        print(f"[DEBUG] API key: {api_key[:20]}...")
        resp = requests.post(CLAUDE_API_URL, headers=headers, json=payload, timeout=30)
        print(f"[DEBUG] Status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"[DEBUG] Error response: {resp.text}")
            return None
        
        data = resp.json()
        if data.get('content') and len(data['content']) > 0:
            text = data['content'][0].get('text', '')
            try:
                suggestion = json.loads(text)
                return suggestion
            except:
                print(f"[DEBUG] JSON parse failed: {text[:200]}")
                return None
    except Exception as e:
        print(f"[ERROR] {str(e)}")
    
    return None

def main():
    print("[*] Gathering system state...")
    state = gather_state()
    print(f"[✓] Oracle: {state['oracle']}")
    print(f"[✓] Health: {state['health']}")
    print(f"[✓] Wallets: {state['wallets'].get('count')} | ${state['wallets'].get('total', 0):,.0f}")
    print(f"[✓] Ledger: {state['ledger'].get('total')} entries")
    
    print("\n[*] Getting suggestion from Claude...")
    suggestion = get_claude_suggestion(state)
    
    if suggestion:
        print(f"\n[✓] SUGGESTION: {suggestion['suggestion']}")
        print(f"    {suggestion['description']}")
        print(f"    Risk: {suggestion['risk']} | Time: {suggestion['time_estimate']}")
    else:
        print("[ERROR] Failed to get suggestion")

if __name__ == "__main__":
    main()
