#!/usr/bin/env python3
# omega_morning_briefing.py
# Daily 8am system health report via Telegram

import os, sys, urllib.request, urllib.parse, json, subprocess
from datetime import datetime
import psycopg2

def _env(key):
    for l in open("/data/data/com.termux/files/home/.env").read().splitlines():
        if l.startswith(key + "="):
            return l.split("=",1)[1].strip()
    return ""

BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
CHAT_ID   = _env("TELEGRAM_CHAT_ID")

def notify(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": msg}).encode()
    urllib.request.urlopen(url, data=data, timeout=10)

def get_oracle():
    try:
        result = subprocess.run(
            ["python3", "/data/data/com.termux/files/home/omega_oracle_v2.py", "score"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PGPASSWORD": "omega"}
        )
        for line in result.stdout.splitlines():
            if "SYSTEM SCORE" in line:
                return line.strip()
        return "Oracle: unavailable"
    except:
        return "Oracle: unavailable"

def get_nft_sales():
    try:
        conn = psycopg2.connect("dbname=omega_ledger user=postgres host=127.0.0.1 port=5432")
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*), COALESCE(SUM(
                CASE rarity
                    WHEN 'Impossible Diamond' THEN 2500
                    WHEN 'Black Diamond' THEN 500
                    WHEN 'Super Rare' THEN 150
                    WHEN 'Rare' THEN 75
                    WHEN 'Medium' THEN 35
                    ELSE 15 END
            ), 0)
            FROM nft_registry WHERE sale_status = 'sold'
        """)
        count, revenue = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM nft_registry WHERE sale_status = 'for_sale'")
        available = cur.fetchone()[0]
        conn.close()
        return f"Sold: {count} tokens | Revenue: ${revenue:,.0f} | Available: {available}"
    except Exception as e:
        return f"NFT data unavailable: {e}"

def get_top_wallets():
    try:
        conn = psycopg2.connect("dbname=omega_bank user=postgres host=127.0.0.1 port=5432")
        cur = conn.cursor()
        cur.execute("""
            SELECT a.owner_name, w.settled_balance
            FROM wallets w JOIN accounts a ON w.account_id = a.account_id
            ORDER BY w.settled_balance DESC LIMIT 3
        """)
        rows = cur.fetchall()
        conn.close()
        return "\n".join([f"  {r[0][:25]}: ${float(r[1]):,.2f}" for r in rows])
    except:
        return "Wallet data unavailable"

def get_tunnels():
    try:
        result = urllib.request.urlopen("http://127.0.0.1:8085/current-all", timeout=5)
        data = json.loads(result.read())
        gallery = data.get("gallery", "N/A")
        api = data.get("api", "N/A")
        return f"Gallery: {gallery[:40]}\nAPI: {api[:40]}"
    except:
        return "Tunnels: unavailable"

def get_phone2():
    try:
        result = subprocess.run(
            ["ssh", "-i", "/data/data/com.termux/files/home/.ssh/omega_bridge",
             "-p", "8022", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
             "u0_a253@192.168.11.2", "echo ONLINE"],
            capture_output=True, text=True, timeout=8
        )
        return "Phone 2: ONLINE ✅" if "ONLINE" in result.stdout else "Phone 2: UNREACHABLE ⚠️"
    except:
        return "Phone 2: UNREACHABLE ⚠️"

def send_briefing():
    now = datetime.now().strftime("%A %b %d, %Y — %I:%M %p")
    oracle = get_oracle()
    nft = get_nft_sales()
    wallets = get_top_wallets()
    tunnels = get_tunnels()
    phone2 = get_phone2()

    msg = f"""🌅 OMEGA MORNING BRIEFING
{now}

📊 {oracle}

🎨 NFT STATUS
{nft}

💰 TOP WALLETS
{wallets}

🌐 TUNNELS
{tunnels}

📱 {phone2}

Ω Omega Art Studio — Built on two phones."""

    notify(msg)
    print("Briefing sent.")

def install():
    """Add to crontab for 8am daily"""
    cron_line = "0 8 * * * python3 /data/data/com.termux/files/home/omega_morning_briefing.py"
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout
    if "omega_morning_briefing" not in existing:
        new_cron = existing.rstrip() + "\n" + cron_line + "\n"
        proc = subprocess.run(["crontab", "-"], input=new_cron, text=True)
        print("Installed to crontab — runs daily at 8am")
    else:
        print("Already in crontab")
    send_briefing()

if __name__ == "__main__":
    if "--install" in sys.argv:
        install()
    else:
        send_briefing()
