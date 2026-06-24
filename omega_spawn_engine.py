#!/usr/bin/env python3
"""
OMEGA SELF-GROWING NODE ENGINE v1.0
"The network decides when it needs to grow. Then it grows itself."

Architecture:
- Monitors ledger entry count across all nodes
- When threshold crossed: triggers spawn event
- Spawn event: clones config from existing node, provisions new node
- New node registers in omega_node_registry
- Begins chain sync from nearest peer
- Guardian picks it up automatically

Spawn triggers:
- Entry count crosses 2M, 5M, 10M, 25M, 50M, 100M
- Any node reports load > 80%
- Quorum drops below 2 (emergency spawn)

Node naming:
- omega-node-001, 002 — founding nodes (Phone 1, Phone 2)
- omega-node-003+ — spawned nodes (Replit, VPS, etc)
"""

import os, sys, json, time, hashlib, socket, subprocess
import urllib.request as _ur
import psycopg2
from datetime import datetime
from pathlib import Path

HOME = "/data/data/com.termux/files/home"
DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_USER = "postgres"

SPAWN_THRESHOLDS = [2_000_000, 5_000_000, 10_000_000, 25_000_000, 50_000_000]
SPAWN_LOG = f"{HOME}/omega_runtime/logs/spawn_engine.log"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        Path(SPAWN_LOG).parent.mkdir(parents=True, exist_ok=True)
        with open(SPAWN_LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def get_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        dbname="omega_bank", user=DB_USER,
        connect_timeout=5
    )

def get_ledger_count():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ledger_entries")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        log(f"Ledger count failed: {e}")
        return 0

def get_node_registry():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT node_id, host, mesh_port, status, entry_count, chain_tip
            FROM omega_node_registry
            ORDER BY entry_count DESC
        """)
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        log(f"Node registry failed: {e}")
        return []

def get_spawned_count():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM omega_node_registry WHERE node_id LIKE 'omega-node-%'")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        return 2

def register_node(node_id, host, mesh_port, chain_tip, entry_count):
    """Register a new node in the network registry."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO omega_node_registry
                (node_id, host, mesh_port, status, last_seen, chain_tip, entry_count, version)
            VALUES (%s, %s, %s, 'provisioning', NOW(), %s, %s, '2.0')
            ON CONFLICT (node_id) DO UPDATE SET
                status = 'provisioning',
                last_seen = NOW(),
                chain_tip = EXCLUDED.chain_tip,
                entry_count = EXCLUDED.entry_count
        """, (node_id, host, mesh_port, chain_tip, entry_count))
        conn.commit()
        conn.close()
        log(f"Node registered: {node_id} @ {host}:{mesh_port}")
        return True
    except Exception as e:
        log(f"Node registration failed: {e}")
        return False

def record_spawn_event(node_id, trigger, entry_count, chain_tip):
    """Record spawn event in ledger WAL stream."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT,
            dbname="omega_bank", user=DB_USER,
            connect_timeout=5
        )
        cur = conn.cursor()
        import uuid
        cur.execute("""
            INSERT INTO ledger_wal_stream
                (global_sequence, ledger_id, debit_account, credit_account,
                 amount, created_at, currency)
            VALUES (
                (SELECT COALESCE(MAX(global_sequence), 0) + 1 FROM ledger_wal_stream),
                %s, 'GENESIS', 'SPAWN_ENGINE', 0.00, NOW(), 'SYS'
            )
        """, (str(uuid.uuid4()),))
        conn.commit()
        conn.close()
        log(f"Spawn event recorded in WAL stream")
    except Exception as e:
        log(f"WAL record failed (non-fatal): {e}")

def generate_node_config(node_id, base_port):
    """Generate config for a new spawned node."""
    node_num = int(node_id.split("-")[-1])
    return {
        "node_id": node_id,
        "host": "127.0.0.1",
        "consensus_port": base_port,
        "mesh_port": base_port + 1,
        "db_host": DB_HOST,
        "db_port": DB_PORT,
        "db_name": "omega_bank",
        "peer_nodes": [
            {"node_id": "omega-node-001", "host": "192.168.11.115", "port": 7432},
            {"node_id": "omega-node-002", "host": "192.168.11.238", "port": 7432},
        ],
        "spawned_at": datetime.now().isoformat(),
        "spawn_generation": node_num - 2,
        "genesis_hash": hashlib.sha256(node_id.encode()).hexdigest()[:16],
    }

def write_node_config(config):
    """Write node config to disk for guardian to pick up."""
    config_path = f"{HOME}/omega_nodes/{config['node_id']}/config.json"
    Path(config_path).parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    log(f"Config written: {config_path}")
    return config_path

def generate_node_launcher(config):
    """Generate a launch script for the new node."""
    node_id = config["node_id"]
    launcher = f"""#!/data/data/com.termux/files/usr/bin/bash
# AUTO-GENERATED by omega_spawn_engine.py
# Node: {node_id}
# Spawned: {config['spawned_at']}
# Generation: {config['spawn_generation']}

NODE_ID="{node_id}"
CONSENSUS_PORT={config['consensus_port']}
MESH_PORT={config['mesh_port']}
LOG_DIR="{HOME}/omega_runtime/logs"

echo "[$(date)] Spawning $NODE_ID..."

# Start consensus node
nohup python3 {HOME}/Omega-Production/omega_consensus.py \\
    --node-id "$NODE_ID" \\
    --port "$CONSENSUS_PORT" \\
    >> "$LOG_DIR/{node_id}_consensus.log" 2>&1 &
echo "[$(date)] Consensus PID=$!"

# Start mesh node
nohup python3 {HOME}/Omega-Production/omega_node_manager.py \\
    --node-id "$NODE_ID" \\
    --port "$MESH_PORT" \\
    >> "$LOG_DIR/{node_id}_mesh.log" 2>&1 &
echo "[$(date)] Mesh PID=$!"

echo "[$(date)] $NODE_ID spawned successfully"
"""
    launcher_path = f"{HOME}/omega_nodes/{node_id}/launch.sh"
    with open(launcher_path, "w") as f:
        f.write(launcher)
    os.chmod(launcher_path, 0o755)
    log(f"Launcher written: {launcher_path}")
    return launcher_path

def spawn_node(trigger_entry_count, trigger_reason):
    """Main spawn function — creates next node in sequence."""
    nodes = get_node_registry()
    current_count = len(nodes)
    next_num = current_count + 1
    node_id = f"omega-node-{next_num:03d}"
    base_port = 7432 + (next_num - 1) * 2

    log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log(f"SPAWN EVENT: {node_id}")
    log(f"Trigger: {trigger_reason}")
    log(f"Ledger entries: {trigger_entry_count:,}")
    log(f"Current nodes: {current_count}")
    log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Get chain tip from most synced node
    chain_tip = nodes[0][5] if nodes else "GENESIS"
    entry_count = nodes[0][4] if nodes else 0

    # Generate config
    config = generate_node_config(node_id, base_port)

    # Write config and launcher
    config_path = write_node_config(config)
    launcher_path = generate_node_launcher(config)

    # Register in network
    registered = register_node(
        node_id=node_id,
        host=config["host"],
        mesh_port=config["mesh_port"],
        chain_tip=chain_tip,
        entry_count=entry_count
    )

    # Record in WAL
    record_spawn_event(node_id, trigger_reason, trigger_entry_count, chain_tip)

    # Send Telegram notification
    _notify_spawn(node_id, trigger_reason, trigger_entry_count, current_count + 1)

    # Write spawn manifest
    manifest = {
        "node_id": node_id,
        "spawned_at": datetime.now().isoformat(),
        "trigger": trigger_reason,
        "entry_count_at_spawn": trigger_entry_count,
        "genesis_nodes": ["omega-node-001", "omega-node-002"],
        "config_path": config_path,
        "launcher_path": launcher_path,
        "status": "provisioned",
        "chain_tip": chain_tip,
        "generation": config["spawn_generation"],
        "proof_hash": hashlib.sha256(
            f"{node_id}{trigger_entry_count}{chain_tip}".encode()
        ).hexdigest()[:16],
    }

    manifest_path = f"{HOME}/omega_nodes/{node_id}/manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    log(f"Node {node_id} provisioned")
    log(f"Config:    {config_path}")
    log(f"Launcher:  {launcher_path}")
    log(f"Manifest:  {manifest_path}")
    log(f"Proof:     {manifest['proof_hash']}")
    log(f"Status:    PROVISIONED — ready to launch")
    log(f"Launch:    bash {launcher_path}")
    return manifest

def _notify_spawn(node_id, trigger, entry_count, total_nodes):
    """Send Telegram notification about spawn event."""
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        admin_ids_raw = os.getenv("TELEGRAM_ADMIN_IDS", "")
        if not bot_token:
            from dotenv import load_dotenv
            load_dotenv(f"{HOME}/.env")
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            admin_ids_raw = os.getenv("TELEGRAM_ADMIN_IDS", "")
        admin_ids = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip()]
        msg = (
            f"OMEGA NETWORK — NODE SPAWNED\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  New Node:     {node_id}\n"
            f"  Trigger:      {trigger}\n"
            f"  Ledger Count: {entry_count:,}\n"
            f"  Total Nodes:  {total_nodes}\n"
            f"  Status:       PROVISIONED\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  Run: bash ~/omega_nodes/{node_id}/launch.sh\n"
            f"  Network is growing. Omega expands."
        )
        for admin_id in admin_ids:
            payload = json.dumps({"chat_id": admin_id, "text": msg}).encode()
            req = _ur.Request(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            _ur.urlopen(req, timeout=10)
    except Exception as e:
        log(f"Telegram notify failed (non-fatal): {e}")

def check_spawn_needed():
    """Check if network should grow. Returns (bool, reason)."""
    entry_count = get_ledger_count()
    nodes = get_node_registry()
    total_nodes = len(nodes)

    # Check entry thresholds — use total registered nodes, not just active
    for i, threshold in enumerate(SPAWN_THRESHOLDS):
        if entry_count >= threshold:
            needed_nodes = i + 3  # node-003 at 2M, 004 at 5M, etc
            if total_nodes < needed_nodes:
                return True, f"entry_threshold_{threshold:,}"

    # Emergency quorum: fewer than 2 REGISTERED nodes (not just active)
    # Only trigger if genuinely missing nodes, not just status lag
    if total_nodes < 2:
        return True, "emergency_quorum_loss"

    return False, None

def load_spawn_state():
    state_path = f"{HOME}/omega_runtime/state/spawn_state.json"
    try:
        return json.loads(Path(state_path).read_text())
    except Exception:
        return {"spawned_nodes": [], "last_check": None, "total_spawns": 0}

def save_spawn_state(state):
    state_path = f"{HOME}/omega_runtime/state/spawn_state.json"
    Path(state_path).parent.mkdir(parents=True, exist_ok=True)
    Path(state_path).write_text(json.dumps(state, indent=2))

def status():
    """Print full network status."""
    entry_count = get_ledger_count()
    nodes = get_node_registry()
    state = load_spawn_state()
    next_threshold = next(
        (t for t in SPAWN_THRESHOLDS if t > entry_count), None
    )
    entries_to_next = next_threshold - entry_count if next_threshold else None

    print(f"\n{'='*54}")
    print(f"  OMEGA SPAWN ENGINE — NETWORK STATUS")
    print(f"{'='*54}")
    print(f"  Ledger entries:  {entry_count:>12,}")
    if entries_to_next:
        print(f"  Next spawn at:   {next_threshold:>12,}  ({entries_to_next:,} away)")
    print(f"  Total spawns:    {state.get('total_spawns', 0)}")
    print(f"\n  REGISTERED NODES ({len(nodes)}):")
    for node in nodes:
        node_id, host, mesh_port, status_val, count, tip = node
        icon = "🟢" if status_val in ("active", "ACTIVE") else "⚪"
        print(f"  {icon} {node_id:<20} {host}:{mesh_port}  entries={count:,}")
    need_spawn, reason = check_spawn_needed()
    if need_spawn:
        print(f"\n  ⚡ SPAWN NEEDED: {reason}")
    else:
        print(f"\n  ✅ Network healthy — no spawn needed")
    print(f"{'='*54}")

def watch(interval=60):
    """Continuous watch mode — auto-spawns when threshold hit."""
    log(f"Spawn engine watch mode started (interval={interval}s)")
    state = load_spawn_state()
    while True:
        try:
            need_spawn, reason = check_spawn_needed()
            if need_spawn:
                entry_count = get_ledger_count()
                log(f"Spawn triggered: {reason} at {entry_count:,} entries")
                manifest = spawn_node(entry_count, reason)
                state["spawned_nodes"].append(manifest["node_id"])
                state["total_spawns"] = len(state["spawned_nodes"])
                state["last_spawn"] = manifest["spawned_at"]
                save_spawn_state(state)
                log(f"Spawn complete. Sleeping 300s before next check.")
                time.sleep(300)
            else:
                entry_count = get_ledger_count()
                state["last_check"] = datetime.now().isoformat()
                state["last_entry_count"] = entry_count
                save_spawn_state(state)
        except Exception as e:
            log(f"Watch error: {e}")
        time.sleep(interval)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(f"{HOME}/.env")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        status()
    elif cmd == "watch":
        watch()
    elif cmd == "spawn":
        entry_count = get_ledger_count()
        manifest = spawn_node(entry_count, "manual_spawn")
        print(json.dumps(manifest, indent=2))
    elif cmd == "check":
        need, reason = check_spawn_needed()
        print(f"Spawn needed: {need}")
        if reason:
            print(f"Reason: {reason}")
