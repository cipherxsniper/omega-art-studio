#!/usr/bin/env python3
"""
OMEGA TUNNEL WATCHDOG
Monitors SSH tunnel to Phone 2, auto-restarts if it dies.
Runs as a background daemon inside omega_guardian.
"""
import subprocess, time, logging, os
from pathlib import Path

LOG = logging.getLogger("TunnelWatchdog")
logging.basicConfig(level=logging.INFO,
    format="[%(asctime)s] [%(name)s] %(message)s")

TUNNEL_CMD = [
    "ssh", "-i", str(Path.home() / ".ssh/omega_bridge"),
    "-o", "StrictHostKeyChecking=no",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=5",
    "-L", "5432:127.0.0.1:5432",
    "u0_a253@192.168.11.163",
    "-p", "8022", "-N"
]

def tunnel_alive():
    try:
        r = subprocess.run(
            ["pg_isready", "-h", "127.0.0.1", "-p", "5432"],
            capture_output=True, timeout=5
        )
        return r.returncode == 0
    except:
        return False

def kill_old_tunnel():
    subprocess.run(["pkill", "-f", "L 5432"], capture_output=True)
    time.sleep(2)

def start_tunnel():
    log_path = Path.home() / "omega_runtime/logs/ssh_tunnel.log"
    with open(log_path, "a") as log:
        subprocess.Popen(TUNNEL_CMD, stdout=log, stderr=log)
    time.sleep(6)

def run():
    LOG.info("Tunnel watchdog started")
    while True:
        if not tunnel_alive():
            LOG.warning("Tunnel down — restarting...")
            kill_old_tunnel()
            start_tunnel()
            if tunnel_alive():
                LOG.info("Tunnel restored ✅")
            else:
                LOG.error("Tunnel restart failed ❌")
        time.sleep(30)

if __name__ == "__main__":
    run()
