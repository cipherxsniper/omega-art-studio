#!/usr/bin/env python3
"""
OMEGA SELF-HEALER — autonomous recovery engine
Called by the Oracle after scoring. Runs component-specific playbooks,
re-checks, logs outcomes, sends Telegram alerts.
Never modifies scores — healing happens AFTER honest scoring.
"""
import json, subprocess, time, hashlib
from pathlib import Path
from datetime import datetime, timezone

HOME         = Path("/data/data/com.termux/files/home")
HEAL_LOG     = HOME / "omega_runtime/logs/self_healer.log"
VPS_REGISTRY = HOME / "omega_runtime/vps_registry.json"
ENV_FILE     = HOME / ".env"

def ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def log(msg):
    HEAL_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = f"[{ts()}] {msg}"
    print(f"  🔧 {msg}")
    with open(HEAL_LOG, "a") as f:
        f.write(entry + "\n")

def get_bot_token():
    try:
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"')
    except:
        pass
    return None

def get_chat_id():
    try:
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("TELEGRAM_CHAT_ID=") or line.startswith("OWNER_CHAT_ID="):
                return line.split("=", 1)[1].strip().strip('"')
    except:
        pass
    return None

def telegram_alert(msg):
    token = get_bot_token()
    chat  = get_chat_id()
    if not token or not chat:
        return
    try:
        import urllib.request, urllib.parse
        payload = json.dumps({"chat_id": chat, "text": f"🔧 OMEGA SELF-HEALER\n{msg}"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)
    except:
        pass

def check_port(port, timeout=3):
    try:
        import urllib.request
        r = urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=timeout)
        data = json.loads(r.read())
        return data.get("status") == "healthy"
    except:
        return False

def heal_omega_cloud():
    """Restart any dead VPS instance server.py processes."""
    try:
        registry = json.loads(VPS_REGISTRY.read_text())
        instances = registry.get("instances", {})
    except Exception as e:
        log(f"omega_cloud: could not read registry: {e}")
        return False

    healed_any = False
    for inst_id, inst in instances.items():
        if inst.get("status") != "ACTIVE":
            continue
        port = inst.get("port")
        if not port:
            continue
        if check_port(port):
            continue  # already healthy, skip

        log(f"omega_cloud: instance {inst_id[:8]} port {port} is down — attempting restart")
        server_py = HOME / "omega_runtime/vps_instances" / inst_id / "server.py"
        if not server_py.exists():
            log(f"omega_cloud: server.py not found at {server_py}")
            continue

        # Kill any zombie process on that port first
        subprocess.run(
            f"fuser -k {port}/tcp 2>/dev/null || true",
            shell=True, capture_output=True
        )
        time.sleep(1)

        # Restart
        subprocess.Popen(
            ["python3", str(server_py)],
            stdout=open(HOME / f"omega_runtime/logs/vps_{inst_id[:8]}.log", "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        time.sleep(3)

        if check_port(port):
            log(f"omega_cloud: AUTO-HEALED instance {inst_id[:8]} on port {port}")
            telegram_alert(f"✅ AUTO-HEALED: omega_cloud instance {inst_id[:8]} (port {port}) restarted successfully.")
            healed_any = True
        else:
            log(f"omega_cloud: HEAL_FAILED instance {inst_id[:8]} on port {port} — still unreachable after restart")
            telegram_alert(f"❌ HEAL_FAILED: omega_cloud instance {inst_id[:8]} (port {port}) did not recover. Manual check needed.")

    return healed_any

def heal_omega_frozen():
    """Re-run the frozen registry verify. If it fails, restart the frozen registry process."""
    frozen_script = HOME / "omega_frozen_registry.py"
    if not frozen_script.exists():
        log("omega_frozen: omega_frozen_registry.py not found")
        return False

    # First attempt: just re-verify
    result = subprocess.run(
        ["python3", str(frozen_script), "verify"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        log("omega_frozen: re-verify passed — transient failure, now clean")
        telegram_alert("✅ AUTO-HEALED: omega_frozen re-verified successfully (transient failure).")
        return True

    log(f"omega_frozen: re-verify failed: {result.stdout.strip()[:200]}")

    # Second attempt: kill any stuck process and restart
    subprocess.run("pkill -f omega_frozen_registry.py 2>/dev/null || true", shell=True)
    time.sleep(2)

    subprocess.Popen(
        ["python3", str(frozen_script), "watch"],
        stdout=open(HOME / "omega_runtime/logs/frozen_registry.log", "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    time.sleep(5)

    result2 = subprocess.run(
        ["python3", str(frozen_script), "verify"],
        capture_output=True, text=True, timeout=30
    )
    if result2.returncode == 0:
        log("omega_frozen: AUTO-HEALED after process restart")
        telegram_alert("✅ AUTO-HEALED: omega_frozen recovered after process restart.")
        return True

    log(f"omega_frozen: HEAL_FAILED — {result2.stdout.strip()[:200]}")
    telegram_alert(f"❌ HEAL_FAILED: omega_frozen could not recover. Manual check needed.")
    return False

PLAYBOOKS = {
    "omega_cloud":  heal_omega_cloud,
    "omega_frozen": heal_omega_frozen,
}

def run(failed_components: list) -> dict:
    """
    Main entry point. Called with list of failed component names.
    Returns dict of {component: "healed"|"failed"|"no_playbook"}
    """
    if not failed_components:
        return {}

    results = {}
    log(f"Self-healer activated — {len(failed_components)} component(s) to attempt: {failed_components}")

    for component in failed_components:
        if component not in PLAYBOOKS:
            log(f"{component}: no playbook registered — skipping")
            results[component] = "no_playbook"
            continue
        try:
            success = PLAYBOOKS[component]()
            results[component] = "healed" if success else "failed"
        except Exception as e:
            log(f"{component}: playbook raised exception: {e}")
            results[component] = "failed"

    healed  = [k for k, v in results.items() if v == "healed"]
    failed  = [k for k, v in results.items() if v == "failed"]
    skipped = [k for k, v in results.items() if v == "no_playbook"]

    summary = []
    if healed:  summary.append(f"healed: {healed}")
    if failed:  summary.append(f"failed: {failed}")
    if skipped: summary.append(f"no playbook: {skipped}")
    log(f"Healing complete — {' | '.join(summary)}")

    return results

if __name__ == "__main__":
    import sys
    components = sys.argv[1:] or ["omega_cloud", "omega_frozen"]
    run(components)
