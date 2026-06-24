#!/usr/bin/env python3
"""
OMEGA MASTER GUARDIAN
Watches all critical processes and auto-restarts anything dead.
Runs forever in background.
"""
import subprocess, time, os
from pathlib import Path

HOME = Path("/data/data/com.termux/files/home")
LOG  = HOME / "omega_runtime/logs/guardian.log"

PROCESSES = [
    ("omega_v10",          ["python3", str(HOME / "omega_v10.py")]),
    ("omega_tunnel_watch", ["python3", str(HOME / "omega_tunnel_watchdog.py")]),
]

def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def is_running(name):
    r = subprocess.run(["pgrep", "-f", name], capture_output=True)
    return r.returncode == 0

def restart(name, cmd):
    log(f"RESTARTING {name}...")
    env = os.environ.copy()
    env["PGPASSWORD"] = "omega"
    with open(HOME / f"omega_runtime/logs/{name}.log", "a") as lf:
        subprocess.Popen(cmd, stdout=lf, stderr=lf, env=env)
    time.sleep(5)
    if is_running(name):
        log(f"{name} RESTORED ✅")
    else:
        log(f"{name} FAILED TO RESTART ❌")

def run():
    log("Master Guardian started")
    while True:
        for name, cmd in PROCESSES:
            if not is_running(name):
                log(f"{name} is DOWN")
                restart(name, cmd)
        time.sleep(30)

if __name__ == "__main__":
    run()
