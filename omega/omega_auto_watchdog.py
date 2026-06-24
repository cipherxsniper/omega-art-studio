#!/usr/bin/env python3
"""
Omega Auto Watchdog — monitors Oracle score and auto-heals
Runs every 60s, alerts Telegram if score drops, attempts fixes
"""
import subprocess, time, json, urllib.request
from pathlib import Path
from datetime import datetime

ENV = Path("/data/data/com.termux/files/home/.env")
HISTORY = Path("/data/data/com.termux/files/home/omega_oracle_history.json")
LOG = Path("/data/data/com.termux/files/home/omega_runtime/logs/watchdog.log")

def env(key):
    for line in ENV.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=",1)[1].strip()
    return ""

def tg(msg):
    try:
        token = env("TELEGRAM_BOT_TOKEN")
        chat  = env("TELEGRAM_CHAT_ID")
        payload = json.dumps({"chat_id": chat, "text": f"🛡 WATCHDOG\n\n{msg}"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload, headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=8)
    except Exception:
        pass

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def get_score():
    try:
        result = subprocess.run(
            ["python3", "/data/data/com.termux/files/home/omega_oracle_v3.py", "score"],
            capture_output=True, text=True, timeout=60
        )
        for line in result.stdout.splitlines():
            if "SYSTEM SCORE:" in line:
                return int(line.split("SYSTEM SCORE:")[1].split("/")[0].strip())
    except Exception:
        pass
    return None

def check_process(name):
    result = subprocess.run(["pgrep", "-f", name], capture_output=True, text=True)
    return bool(result.stdout.strip())

def restart_omega():
    subprocess.run(["pkill", "-f", "omega_v10.py"])
    time.sleep(3)
    subprocess.Popen([
        "nohup", "python3",
        "/data/data/com.termux/files/home/omega_v10.py"
    ], stdout=open("/data/data/com.termux/files/home/omega_runtime/logs/nohup.log", "a"),
       stderr=subprocess.STDOUT)
    log("omega_v10.py restarted")

def restart_tunnel():
    subprocess.run(["pkill", "-f", "omega_bridge"])
    time.sleep(2)
    subprocess.Popen([
        "ssh", "-i", "/data/data/com.termux/files/home/.ssh/omega_bridge",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=30",
        "-L", "5432:127.0.0.1:5432",
        "u0_a253@192.168.11.163", "-p", "8022", "-N"
    ])
    log("SSH tunnel restarted")

best_score = 105  # Known best
last_score = 100

while True:
    try:
        # Check critical processes
        if not check_process("omega_v10.py"):
            log("omega_v10.py DOWN — restarting")
            tg("❌ omega_v10.py was DOWN — auto-restarting")
            restart_omega()
            time.sleep(15)

        if not check_process("omega_bridge"):
            log("SSH tunnel DOWN — restarting")
            tg("❌ SSH tunnel DOWN — auto-restarting")
            restart_tunnel()
            time.sleep(10)

        if not check_process("cloudflared"):
            log("Cloudflared DOWN")
            tg("⚠️ Cloudflared tunnel DOWN — Stripe webhooks offline")

        # Check Oracle score
        score = get_score()
        if score is not None:
            if score < last_score:
                msg = f"⚠️ Oracle score dropped: {last_score} → {score}\nInvestigating..."
                log(msg)
                tg(msg)
            elif score > best_score:
                best_score = score
                log(f"New best score: {score}")
            last_score = score
            log(f"Oracle: {score}/100 | omega: {'UP' if check_process('omega_v10.py') else 'DOWN'}")

        time.sleep(60)

    except KeyboardInterrupt:
        log("Watchdog stopped")
        break
    except Exception as e:
        log(f"Watchdog error: {e}")
        time.sleep(60)
