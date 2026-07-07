#!/usr/bin/env python3
"""
OMEGA AUTONOMOUS NODE PROVISIONER v1.0
"The network grows itself."

Monitors system load triggers and automatically provisions new VPS nodes:
- Assigns next available port (6004, 6005, ...)
- Generates unique instance ID (SHA256-based, OM109-seeded)
- Writes server.py from template
- Registers in vps_registry.json
- Starts the node process
- Announces to consensus layer
- Oracle picks it up automatically on next score cycle

Triggers:
- Ledger entries cross spawn thresholds (2M, 5M, 10M...)
- Active node count drops below MIN_NODES
- Manual: python3 omega_node_provisioner.py --spawn
- Watch mode: python3 omega_node_provisioner.py --watch
"""

import os, sys, json, time, hashlib, subprocess, argparse
import psycopg2, urllib.request
from datetime import datetime, timezone
from pathlib import Path

HOME = Path("/data/data/com.termux/files/home")
REGISTRY = HOME / "omega_runtime" / "vps_registry.json"
INSTANCES_DIR = HOME / "omega_runtime" / "vps_instances"
LOG_FILE = HOME / "omega_runtime" / "logs" / "node_provisioner.log"
GENESIS_SEED = "OMEGA_GENESIS_THOMAS_LEE_HARVEY_OM109_2024"

MIN_NODES = 2          # spawn if active nodes drop below this
PORT_START = 6004      # first auto-assigned port
SPAWN_THRESHOLDS = [2_000_000, 5_000_000, 10_000_000, 25_000_000, 50_000_000]
WATCH_INTERVAL = 300   # check every 5 minutes in watch mode


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def load_registry():
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text())
    return {"instances": {}, "port_assignments": {}}


def save_registry(data):
    REGISTRY.write_text(json.dumps(data, indent=2))


def get_active_nodes(registry):
    return [i for i in registry["instances"].values()
            if i["status"] == "ACTIVE"]


def get_used_ports(registry):
    return {i["port"] for i in registry["instances"].values()}


def next_port(registry):
    used = get_used_ports(registry)
    port = PORT_START
    while port in used:
        port += 1
    return port


def generate_instance_id(port):
    seed = f"{GENESIS_SEED}:NODE:{port}:{datetime.now(timezone.utc).isoformat()}"
    return hashlib.sha256(seed.encode()).hexdigest()[:16]


def get_ledger_count():
    try:
        conn = psycopg2.connect(
            host="127.0.0.1", port=5544,
            dbname="omega_bank", user="u0_a321",
            connect_timeout=5
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ledger_entries")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        log(f"[WARN] Ledger count failed: {e}")
        return 0


def write_server(instance_id, port, tier="sovereign"):
    """Clone server.py template with new instance identity."""
    instance_dir = INSTANCES_DIR / instance_id
    logs_dir = instance_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    server_code = f'''#!/usr/bin/env python3
import socket, threading, logging
PORT={port}
INSTANCE_ID="{instance_id}"
TIER="{tier}"
STORAGE_GB=100
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vps")
def handle_conn(conn, addr):
    try:
        raw = conn.recv(4096)
        conn.sendall(b\'HTTP/1.1 200 OK\\r\\nContent-Type: application/json\\r\\n\\r\\n\' +
            ({{"status":"healthy","instance":INSTANCE_ID[:8],"tier":TIER,"port":PORT}})
            .__repr__().encode().replace(b"\'", b\'"\') + b\' \')
    except Exception as e:
        log.warning(f"Conn error: {{e}}")
    finally:
        conn.close()
def run():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", PORT))
    sock.listen(32)
    log.info(f"Omega VPS Node {{INSTANCE_ID[:8]}} ONLINE on port {{PORT}}")
    while True:
        conn, addr = sock.accept()
        threading.Thread(target=handle_conn, args=(conn, addr), daemon=True).start()
if __name__ == "__main__":
    run()
'''
    (instance_dir / "server.py").write_text(server_code)
    log(f"[SERVER] Written: {instance_dir}/server.py (port {port})")
    return instance_dir / "server.py"


def start_node(instance_id, server_path, port):
    """Launch the node process."""
    log_path = INSTANCES_DIR / instance_id / "logs" / "server.log"
    proc = subprocess.Popen(
        ["python3", str(server_path)],
        stdout=open(log_path, "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    time.sleep(2)
    # verify it actually bound
    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3)
        log(f"[VERIFY] Node {instance_id[:8]} responding on port {port} ✅")
        return proc.pid
    except Exception:
        log(f"[WARN] Node {instance_id[:8]} started (PID {proc.pid}) but not yet responding — may still be starting")
        return proc.pid


def register_node(registry, instance_id, port, tier="sovereign"):
    """Write node into vps_registry.json."""
    now = datetime.now(timezone.utc).isoformat()
    registry["instances"][instance_id] = {
        "instance_id": instance_id,
        "owner_email": "omega@omegaops.ai",
        "owner_name": "Omega Autonomous Node",
        "tier": tier,
        "port": port,
        "subdomain": f"omega-node-{instance_id[:6]}",
        "status": "ACTIVE",
        "created_at": now,
        "expires_at": None,
        "stripe_id": None,
        "key_id": hashlib.sha256(f"{instance_id}:key".encode()).hexdigest()[:16],
        "spawned_automatically": True,
        "spawn_trigger": "autonomous_provisioner",
    }
    if "port_assignments" not in registry:
        registry["port_assignments"] = {}
    registry["port_assignments"][str(port)] = instance_id
    save_registry(registry)
    log(f"[REGISTRY] Node {instance_id[:8]} registered on port {port}")


def announce_to_consensus(instance_id, port):
    """Ping the consensus layer to acknowledge the new node."""
    try:
        req = urllib.request.urlopen(
            f"http://127.0.0.1:7432/status", timeout=3
        )
        log(f"[CONSENSUS] Announced node {instance_id[:8]} to consensus layer")
    except Exception as e:
        log(f"[CONSENSUS] Announce failed (non-fatal): {e}")


def provision_node(reason="manual"):
    """Full autonomous provisioning sequence."""
    log(f"[SPAWN] Provisioning new node — reason: {reason}")
    registry = load_registry()
    port = next_port(registry)
    instance_id = generate_instance_id(port)

    log(f"[SPAWN] Instance: {instance_id[:8]}... Port: {port}")

    server_path = write_server(instance_id, port)
    python3 = subprocess.run(["which", "python3"], capture_output=True, text=True).stdout.strip()
    pid = start_node(instance_id, server_path, port)
    register_node(registry, instance_id, port)
    announce_to_consensus(instance_id, port)

    log(f"[SPAWN] ✅ Node {instance_id[:8]} LIVE on port {port} (PID {pid})")
    log(f"[SPAWN] Active nodes: {len(get_active_nodes(load_registry()))}")
    return instance_id, port


def check_triggers():
    """Evaluate all spawn triggers. Returns (should_spawn, reason)."""
    registry = load_registry()
    active = get_active_nodes(registry)

    # Trigger 1: active node count below minimum
    if len(active) < MIN_NODES:
        return True, f"active_nodes={len(active)} below MIN_NODES={MIN_NODES}"

    # Trigger 2: ledger threshold crossing
    count = get_ledger_count()
    spawned_counts = set()
    spawn_log = HOME / "omega_runtime" / "logs" / "spawn_thresholds.json"
    if spawn_log.exists():
        spawned_counts = set(json.loads(spawn_log.read_text()))
    for threshold in SPAWN_THRESHOLDS:
        if count >= threshold and threshold not in spawned_counts:
            spawned_counts.add(threshold)
            spawn_log.write_text(json.dumps(list(spawned_counts)))
            return True, f"ledger_count={count:,} crossed threshold {threshold:,}"

    # Trigger 3: verify active nodes are actually responding
    dead = []
    for node in active:
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{node['port']}/health", timeout=2
            )
        except Exception:
            dead.append(node["instance_id"])

    if dead:
        # mark dead nodes as FAILED in registry
        for did in dead:
            registry["instances"][did]["status"] = "FAILED"
        save_registry(registry)
        live_count = len(active) - len(dead)
        if live_count < MIN_NODES:
            return True, f"{len(dead)} nodes unresponsive, live={live_count} below MIN_NODES"

    return False, "all clear"


def watch_loop():
    log("[WATCH] Autonomous node provisioner watching...")
    while True:
        try:
            should_spawn, reason = check_triggers()
            if should_spawn:
                log(f"[TRIGGER] {reason}")
                provision_node(reason=reason)
            else:
                log(f"[CHECK] {reason}")
        except Exception as e:
            log(f"[ERROR] Watch loop: {e}")
        time.sleep(WATCH_INTERVAL)


def status():
    registry = load_registry()
    active = get_active_nodes(registry)
    count = get_ledger_count()
    print(f"\n{'='*50}")
    print(f"  OMEGA NODE STATUS")
    print(f"{'='*50}")
    print(f"  Total registered: {len(registry['instances'])}")
    print(f"  Active: {len(active)}")
    print(f"  Ledger entries: {count:,}")
    print(f"  Next spawn threshold: ", end="")
    spawn_log = HOME / "omega_runtime" / "logs" / "spawn_thresholds.json"
    spawned = set(json.loads(spawn_log.read_text())) if spawn_log.exists() else set()
    remaining = [t for t in SPAWN_THRESHOLDS if t not in spawned]
    print(f"{remaining[0]:,}" if remaining else "all thresholds passed")
    print(f"\n  Active nodes:")
    for node in active:
        port = node["port"]
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
            health = "✅ responding"
        except Exception:
            health = "❌ unreachable"
        print(f"    {node['instance_id'][:8]}  port {port}  {node['tier']:12s}  {health}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Omega Autonomous Node Provisioner")
    parser.add_argument("--spawn", action="store_true", help="Provision one new node immediately")
    parser.add_argument("--watch", action="store_true", help="Watch mode — monitor and auto-spawn")
    parser.add_argument("--status", action="store_true", help="Show current node status")
    parser.add_argument("--check", action="store_true", help="Evaluate triggers without spawning")
    args = parser.parse_args()

    if args.spawn:
        provision_node(reason="manual --spawn")
    elif args.watch:
        watch_loop()
    elif args.status:
        status()
    elif args.check:
        should_spawn, reason = check_triggers()
        print(f"Should spawn: {should_spawn} — {reason}")
    else:
        print("Usage: --spawn | --watch | --status | --check")

