#!/usr/bin/env python3
"""
OMEGA DEAD-MAN'S SWITCH v1.0
Monitors cross-phone heartbeat via omega_node_registry.last_seen.
If either phone node hasn't been heard from in 24 hours, alert via
Telegram. Does NOT auto-rebuild — alerts only, human decides.
"""
import os, sys, json
import psycopg2
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request as _ur
from dotenv import load_dotenv

HOME = Path.home()
load_dotenv(HOME / ".env")

DB_HOST = "127.0.0.1"
DB_PORT = 5432

STALE_THRESHOLD_HOURS = 24

WATCH_NODES = {
    "omega-node-001": "Phone 1 (Control Plane, 192.168.11.115)",
    "omega-node-002": "Phone 2 (Database Node, 192.168.11.163)",
}

STATE_PATH = HOME / "omega_runtime/state/deadman_alerts.json"

def get_node_status():
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT,
                                dbname="omega_bank", user="postgres",
                                connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT node_id, last_seen FROM omega_node_registry WHERE node_id IN %s",
                     (tuple(WATCH_NODES.keys()),))
        rows = cur.fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}
    except Exception as e:
        print(f"DB error: {e}")
        return {}

def load_alert_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}

def save_alert_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str))

def notify_telegram(text):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    admin_ids_raw = os.getenv("TELEGRAM_ADMIN_IDS", "")
    if not bot_token or not admin_ids_raw:
        print("Telegram not configured")
        return
    admin_ids = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip()]
    for admin_id in admin_ids:
        try:
            payload = json.dumps({"chat_id": admin_id, "text": text}).encode()
            req = _ur.Request(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                data=payload, headers={"Content-Type": "application/json"}
            )
            _ur.urlopen(req, timeout=10)
        except Exception as e:
            print(f"Telegram send failed: {e}")

def check():
    now = datetime.now(timezone.utc)
    statuses = get_node_status()
    state = load_alert_state()
    threshold = timedelta(hours=STALE_THRESHOLD_HOURS)

    results = []
    for node_id, label in WATCH_NODES.items():
        last_seen = statuses.get(node_id)
        if last_seen is None:
            results.append((node_id, label, "MISSING", None))
            continue

        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)

        age = now - last_seen
        is_stale = age > threshold

        results.append((node_id, label, "STALE" if is_stale else "OK", age))

        already_alerted = state.get(node_id, {}).get("alerted", False)

        if is_stale and not already_alerted:
            hours = age.total_seconds() / 3600
            notify_telegram(
                f"🚨 OMEGA DEAD-MAN'S SWITCH\n\n"
                f"{label}\n"
                f"Node: {node_id}\n"
                f"Last seen: {hours:.1f} hours ago\n\n"
                f"This node has exceeded the {STALE_THRESHOLD_HOURS}h heartbeat threshold. "
                f"Check connectivity, guardian status, and consensus process on this device."
            )
            state[node_id] = {"alerted": True, "alert_ts": now.isoformat()}
        elif not is_stale and already_alerted:
            hours = age.total_seconds() / 3600
            notify_telegram(
                f"✅ OMEGA DEAD-MAN'S SWITCH — RECOVERED\n\n"
                f"{label}\n"
                f"Node: {node_id}\n"
                f"Last seen: {hours:.2f} hours ago — back within threshold."
            )
            state[node_id] = {"alerted": False, "alert_ts": None}

    save_alert_state(state)
    return results

if __name__ == "__main__":
    results = check()
    print(f"\n{'='*54}")
    print(f"  OMEGA DEAD-MAN'S SWITCH — {STALE_THRESHOLD_HOURS}h threshold")
    print(f"{'='*54}")
    for node_id, label, status, age in results:
        icon = {"OK": "🟢", "STALE": "🔴", "MISSING": "⚪"}[status]
        age_str = f"{age.total_seconds()/3600:.2f}h ago" if age else "no data"
        print(f"  {icon} {label}")
        print(f"     {node_id}: last seen {age_str} [{status}]")
    print(f"{'='*54}")
