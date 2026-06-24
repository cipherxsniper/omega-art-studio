#!/usr/bin/env python3
"""
OMEGA LEDGER WATCHER
Scans omega_bank for constitutional violations, chain integrity breaks,
and balance anomalies. Sends Telegram alerts on critical findings,
daily summary report on schedule.
"""
import os, json, urllib.request, urllib.parse, time
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

try:
    import psycopg2
    PG_OK = True
except ImportError:
    PG_OK = False

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT  = os.getenv('TELEGRAM_ADMIN_IDS', '').split(',')[0]
LOG   = os.path.expanduser('~/omega_runtime/logs/ledger_watcher.log')
STATE = os.path.expanduser('~/omega_ledger_watch_state.json')

def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG, 'a') as f:
        f.write(line + '\n')

def tg(msg):
    try:
        data = urllib.parse.urlencode({'chat_id': CHAT, 'text': msg}).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{TOKEN}/sendMessage',
            data=data, method='POST'
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log(f'Telegram send failed: {e}')

def pg():
    return psycopg2.connect(
        host='127.0.0.1', port=5432,
        dbname='omega_bank', user='postgres',
        connect_timeout=5
    )

def check_negative_balances():
    issues = []
    conn = pg(); cur = conn.cursor()
    cur.execute("""
        SELECT a.owner_name, w.available_balance
        FROM wallets w JOIN accounts a ON a.account_id = w.account_id
        WHERE w.available_balance < -0.01
    """)
    for name, bal in cur.fetchall():
        issues.append(f"NEGATIVE BALANCE: {name} = ${bal}")
    conn.close()
    return issues

def check_chain_integrity():
    issues = []
    conn = pg(); cur = conn.cursor()
    cur.execute("""
        SELECT global_sequence, chain_hash, prev_hash
        FROM ledger_entries
        WHERE event_type NOT IN ('STRESS_TEST','STRESS_BILLION')
        ORDER BY global_sequence DESC LIMIT 1000
    """)
    rows = cur.fetchall()
    conn.close()
    broken = 0
    for i in range(len(rows) - 1):
        seq, chain_hash, prev_hash = rows[i]
        next_seq, next_chain, next_prev = rows[i+1]
        if prev_hash != next_chain:
            broken += 1
    if broken > 0:
        issues.append(f"CHAIN BREAK DETECTED: {broken} discontinuities in last 1000 entries")
    return issues

def check_constitutional_violations():
    issues = []
    conn = pg(); cur = conn.cursor()
    cur.execute("""
        SELECT c.invariant_name, c.severity, COUNT(*) as cnt
        FROM omega_invariant_violations v
        JOIN omega_constitution c ON c.id = v.invariant_id
        WHERE v.created_at > NOW() - INTERVAL '24 hours'
        GROUP BY c.invariant_name, c.severity
        ORDER BY cnt DESC
    """)
    for name, severity, cnt in cur.fetchall():
        issues.append(f"VIOLATION [{severity}]: {name} x{cnt} in last 24h")
    conn.close()
    return issues

def check_om109_coverage():
    issues = []
    conn = pg(); cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM ledger_entries
        WHERE event_type NOT IN ('STRESS_TEST','STRESS_BILLION')
        AND om109_fingerprint IS NULL
    """)
    unsigned = cur.fetchone()[0]
    conn.close()
    if unsigned > 0:
        issues.append(f"UNSIGNED ENTRIES: {unsigned} real entries missing OM109 fingerprint")
    return issues

def get_daily_stats():
    conn = pg(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ledger_entries WHERE event_type NOT IN ('STRESS_TEST','STRESS_BILLION')")
    total_entries = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM wallets")
    total_wallets = cur.fetchone()[0]
    cur.execute("SELECT SUM(available_balance) FROM wallets WHERE available_balance > 0")
    total_assets = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM omega_invariant_violations WHERE created_at > NOW() - INTERVAL '24 hours'")
    violations_today = cur.fetchone()[0]
    conn.close()
    return {
        'entries': total_entries,
        'wallets': total_wallets,
        'assets': float(total_assets),
        'violations_today': violations_today
    }

def run_full_scan():
    if not PG_OK:
        log('psycopg2 unavailable — skipping scan')
        return

    all_issues = []
    try:
        all_issues += check_negative_balances()
    except Exception as e:
        log(f'negative balance check failed: {e}')
    try:
        all_issues += check_chain_integrity()
    except Exception as e:
        log(f'chain integrity check failed: {e}')
    try:
        all_issues += check_constitutional_violations()
    except Exception as e:
        log(f'constitutional check failed: {e}')
    try:
        all_issues += check_om109_coverage()
    except Exception as e:
        log(f'om109 check failed: {e}')

    if all_issues:
        log(f'ISSUES FOUND: {len(all_issues)}')
        alert = "OMEGA LEDGER ALERT\n\n" + "\n".join(all_issues)
        tg(alert)
        for i in all_issues:
            log(f'  - {i}')
    else:
        log('Scan clean — no issues')

    return all_issues

def daily_report():
    stats = get_daily_stats()
    msg = (
        f"OMEGA DAILY LEDGER REPORT\n"
        f"{datetime.now().strftime('%Y-%m-%d')}\n\n"
        f"Ledger entries: {stats['entries']:,}\n"
        f"Active wallets: {stats['wallets']}\n"
        f"Total assets: ${stats['assets']:,.2f}\n"
        f"Violations (24h): {stats['violations_today']}\n\n"
        f"Status: {'CLEAN' if stats['violations_today'] == 0 else 'NEEDS REVIEW'}"
    )
    tg(msg)
    log('Daily report sent')

def load_state():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE))
        except:
            pass
    return {'last_daily_report': ''}

def save_state(state):
    json.dump(state, open(STATE, 'w'))

if __name__ == '__main__':
    log('Ledger watcher starting — scan every 10 min, daily report at 21:00')
    while True:
        try:
            run_full_scan()

            state = load_state()
            today = datetime.now().strftime('%Y-%m-%d')
            now_hour = datetime.now().hour
            if now_hour == 21 and state.get('last_daily_report') != today:
                daily_report()
                state['last_daily_report'] = today
                save_state(state)

        except Exception as e:
            log(f'Watcher loop error: {e}')

        time.sleep(600)
