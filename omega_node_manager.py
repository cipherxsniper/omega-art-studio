#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║  OMEGA NODE MANAGER — Self-Organizing Consensus Mesh    ║
║  Centralized-Decentralized Architecture                 ║
║  Nodes discover, register, sync, and rebuild themselves ║
╚══════════════════════════════════════════════════════════╝
"""

import os, sys, json, time, socket, threading, hashlib
import urllib.request as _ur
import urllib.parse as _up
import psycopg2
from datetime import datetime, timezone
from pathlib import Path

# ── Config ─────────────────────────────────────────────
PG_HOST    = "127.0.0.1"
PG_PORT    = 5432
PG_DB      = "omega_bank"
PG_USER    = "postgres"
THIS_HOST  = os.getenv("OMEGA_NODE_HOST", "192.168.11.115")
THIS_ID    = os.getenv("OMEGA_NODE_ID",   "omega-node-001")
MESH_PORT  = int(os.getenv("OMEGA_MESH_PORT", "7433"))
GOSSIP_INT = 10   # seconds between gossip rounds
SYNC_INT   = 30   # seconds between chain sync checks
SPAWN_THR  = 2_000_000  # auto-spawn signal at 2M entries

KNOWN_SEEDS = [
    {"id": "omega-node-001", "host": "192.168.11.115", "port": 7433},
    {"id": "omega-node-002", "host": "192.168.11.2", "port": 7433},
]

# ── Database ────────────────────────────────────────────
def pg():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        dbname=PG_DB, user=PG_USER,
        connect_timeout=5
    )

def pg_exec(sql, params=None, fetch=False):
    try:
        conn = pg()
        cur  = conn.cursor()
        cur.execute(sql, params or [])
        result = cur.fetchall() if fetch else None
        conn.commit()
        conn.close()
        return result
    except Exception as e:
        print(f"[DB] {e}")
        return None

# ── Node Registry ───────────────────────────────────────
def ensure_tables():
    pg_exec("""
        CREATE TABLE IF NOT EXISTS omega_node_registry (
            node_id      TEXT PRIMARY KEY,
            host         TEXT NOT NULL,
            mesh_port    INTEGER DEFAULT 7433,
            status       TEXT DEFAULT 'active',
            last_seen    TIMESTAMP DEFAULT NOW(),
            chain_tip    BIGINT DEFAULT 0,
            entry_count  BIGINT DEFAULT 0,
            version      TEXT DEFAULT '1.0',
            metadata     JSONB DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS omega_node_manifest (
            node_id     TEXT PRIMARY KEY,
            hostname    TEXT,
            config      JSONB,
            version     TEXT,
            updated_at  TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS omega_mesh_events (
            id          SERIAL PRIMARY KEY,
            from_node   TEXT,
            event_type  TEXT,
            payload     JSONB,
            created_at  TIMESTAMP DEFAULT NOW()
        );
    """)

def register_self():
    rows = pg_exec(
        "SELECT COUNT(*) FROM ledger_entries", fetch=True
    )
    count = rows[0][0] if rows else 0
    seq_rows = pg_exec(
        "SELECT MAX(global_sequence) FROM ledger_entries", fetch=True
    )
    tip = seq_rows[0][0] if seq_rows and seq_rows[0][0] else 0

    pg_exec("""
        INSERT INTO omega_node_registry
            (node_id, host, mesh_port, status, last_seen, chain_tip, entry_count, version)
        VALUES (%s, %s, %s, 'active', NOW(), %s, %s, '2.0')
        ON CONFLICT (node_id) DO UPDATE SET
            host=EXCLUDED.host,
            mesh_port=EXCLUDED.mesh_port,
            status='active',
            last_seen=NOW(),
            chain_tip=EXCLUDED.chain_tip,
            entry_count=EXCLUDED.entry_count,
            version='2.0'
    """, [THIS_ID, THIS_HOST, MESH_PORT, tip, count])

    pg_exec("""
        INSERT INTO omega_node_manifest (node_id, hostname, config, version, updated_at)
        VALUES (%s, %s, %s, '2.0', NOW())
        ON CONFLICT (node_id) DO UPDATE SET
            hostname=EXCLUDED.hostname,
            config=EXCLUDED.config,
            updated_at=NOW()
    """, [THIS_ID, THIS_HOST, json.dumps({
        "host": THIS_HOST,
        "mesh_port": MESH_PORT,
        "pg_host": PG_HOST,
        "pg_port": PG_PORT,
    })])
    print(f"[{THIS_ID}] Registered — {count:,} entries, chain_tip={tip}")

def get_all_nodes():
    rows = pg_exec("""
        SELECT node_id, host, mesh_port, status, last_seen, chain_tip, entry_count
        FROM omega_node_registry
        ORDER BY entry_count DESC
    """, fetch=True)
    return rows or []

def mark_node_status(node_id, status):
    pg_exec(
        "UPDATE omega_node_registry SET status=%s, last_seen=NOW() WHERE node_id=%s",
        [status, node_id]
    )

# ── Mesh TCP Server ─────────────────────────────────────
def handle_peer(conn, addr):
    try:
        data = conn.recv(4096).decode()
        msg  = json.loads(data)
        mtype = msg.get("type")

        if mtype == "ping":
            rows = pg_exec("SELECT COUNT(*) FROM ledger_entries", fetch=True)
            count = rows[0][0] if rows else 0
            seq = pg_exec("SELECT MAX(global_sequence) FROM ledger_entries", fetch=True)
            tip = seq[0][0] if seq and seq[0][0] else 0
            resp = {
                "type": "pong",
                "node_id": THIS_ID,
                "host": THIS_HOST,
                "entry_count": count,
                "chain_tip": tip,
                "ts": datetime.now(timezone.utc).isoformat()
            }
            conn.send(json.dumps(resp).encode())
            # Update their registry entry
            pg_exec("""
                INSERT INTO omega_node_registry
                    (node_id, host, mesh_port, status, last_seen, chain_tip, entry_count)
                VALUES (%s, %s, %s, 'active', NOW(), %s, %s)
                ON CONFLICT (node_id) DO UPDATE SET
                    status='active', last_seen=NOW(),
                    chain_tip=EXCLUDED.chain_tip,
                    entry_count=EXCLUDED.entry_count
            """, [msg.get("node_id", "unknown"), msg.get("host", addr[0]),
                  msg.get("mesh_port", 7433),
                  msg.get("chain_tip", 0), msg.get("entry_count", 0)])

        elif mtype == "announce":
            # New node announcing itself
            node_id = msg["node_id"]
            host    = msg["host"]
            port    = msg.get("mesh_port", 7433)
            pg_exec("""
                INSERT INTO omega_node_registry
                    (node_id, host, mesh_port, status, last_seen)
                VALUES (%s, %s, %s, 'active', NOW())
                ON CONFLICT (node_id) DO UPDATE SET
                    host=EXCLUDED.host, status='active', last_seen=NOW()
            """, [node_id, host, port])
            pg_exec(
                "INSERT INTO omega_mesh_events (from_node, event_type, payload) VALUES (%s, %s, %s)",
                [node_id, "NODE_ANNOUNCE", json.dumps(msg)]
            )
            resp = {"type": "welcome", "from": THIS_ID, "nodes": len(get_all_nodes())}
            conn.send(json.dumps(resp).encode())
            print(f"[MESH] New node announced: {node_id} @ {host}:{port}")

        elif mtype == "sync_request":
            # Peer wants chain state
            after_seq = msg.get("after_seq", 0)
            rows = pg_exec("""
                SELECT global_sequence, debit_account, credit_account,
                       amount, chain_hash, created_at
                FROM ledger_entries
                WHERE global_sequence > %s
                ORDER BY global_sequence ASC LIMIT 100
            """, [after_seq], fetch=True)
            entries = [
                {"seq": r[0], "debit": r[1], "credit": r[2],
                 "amount": str(r[3]), "hash": r[4], "ts": str(r[5])}
                for r in (rows or [])
            ]
            resp = {"type": "sync_response", "entries": entries, "from": THIS_ID}
            conn.send(json.dumps(resp).encode())

        elif mtype == "spawn_signal":
            # Another node requesting we spawn a new node
            print(f"[MESH] Spawn signal received from {msg.get('from_node')}")
            pg_exec(
                "INSERT INTO omega_mesh_events (from_node, event_type, payload) VALUES (%s, %s, %s)",
                [msg.get("from_node"), "SPAWN_SIGNAL", json.dumps(msg)]
            )
            resp = {"type": "spawn_ack", "from": THIS_ID}
            conn.send(json.dumps(resp).encode())

    except Exception as e:
        print(f"[MESH] Peer handler error: {e}")
    finally:
        conn.close()

def start_mesh_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", MESH_PORT))
    server.listen(10)
    print(f"[{THIS_ID}] Mesh server listening on :{MESH_PORT}")
    while True:
        try:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_peer, args=(conn, addr), daemon=True)
            t.start()
        except Exception as e:
            print(f"[MESH] Server error: {e}")

# ── Gossip Engine ───────────────────────────────────────
def send_to_peer(host, port, msg):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        s.send(json.dumps(msg).encode())
        resp = s.recv(4096).decode()
        s.close()
        return json.loads(resp)
    except Exception as e:
        return None

def gossip_round():
    nodes = get_all_nodes()
    my_rows = pg_exec("SELECT COUNT(*) FROM ledger_entries", fetch=True)
    my_count = my_rows[0][0] if my_rows else 0
    my_seq = pg_exec("SELECT MAX(global_sequence) FROM ledger_entries", fetch=True)
    my_tip = my_seq[0][0] if my_seq and my_seq[0][0] else 0

    ping_msg = {
        "type": "ping",
        "node_id": THIS_ID,
        "host": THIS_HOST,
        "mesh_port": MESH_PORT,
        "entry_count": my_count,
        "chain_tip": my_tip,
        "ts": datetime.now(timezone.utc).isoformat()
    }

    active = 0
    for node in nodes:
        node_id, host, port = node[0], node[1], node[2]
        if node_id == THIS_ID:
            continue
        resp = send_to_peer(host, port, ping_msg)
        if resp and resp.get("type") == "pong":
            active += 1
            mark_node_status(node_id, "active")
        else:
            mark_node_status(node_id, "unreachable")

    # Update self
    register_self()
    print(f"[GOSSIP] Round complete — {active}/{len(nodes)-1} peers active | entries={my_count:,} tip={my_tip}")

    # Check spawn threshold
    if my_count >= SPAWN_THR:
        check_spawn_signal(my_count, nodes)

def check_spawn_signal(count, nodes):
    active_nodes = [n for n in nodes if n[3] == "active"]
    if len(active_nodes) < 4:
        print(f"[SPAWN] {count:,} entries — signaling need for new node")
        pg_exec(
            "INSERT INTO omega_mesh_events (from_node, event_type, payload) VALUES (%s, %s, %s)",
            [THIS_ID, "SPAWN_NEEDED", json.dumps({
                "entry_count": count,
                "active_nodes": len(active_nodes),
                "recommended_new_nodes": 4 - len(active_nodes)
            })]
        )
        # Broadcast spawn signal to all peers
        for node in nodes:
            if node[0] != THIS_ID:
                send_to_peer(node[1], node[2], {
                    "type": "spawn_signal",
                    "from_node": THIS_ID,
                    "entry_count": count
                })

# ── Chain Sync ──────────────────────────────────────────
def sync_chain_from_peers():
    nodes = get_all_nodes()
    my_seq = pg_exec("SELECT MAX(global_sequence) FROM ledger_entries", fetch=True)
    my_tip = my_seq[0][0] if my_seq and my_seq[0][0] else 0

    for node in nodes:
        node_id, host, port, status = node[0], node[1], node[2], node[3]
        if node_id == THIS_ID or status != "active": continue
        if node[5] and node[5] > my_tip:
            print(f"[SYNC] {node_id} has tip={node[5]}, we have {my_tip} — requesting sync")
            resp = send_to_peer(host, port, {
                "type": "sync_request",
                "from_node": THIS_ID,
                "after_seq": my_tip
            })
            if resp and resp.get("entries"):
                print(f"[SYNC] Received {len(resp['entries'])} entries from {node_id}")

# ── Announce Self to Network ────────────────────────────
def announce_to_network():
    for seed in KNOWN_SEEDS:
        if seed["id"] == THIS_ID: continue
        resp = send_to_peer(seed["host"], seed["port"], {
            "type": "announce",
            "node_id": THIS_ID,
            "host": THIS_HOST,
            "mesh_port": MESH_PORT,
        })
        if resp:
            print(f"[ANNOUNCE] Welcome from {seed['id']} — network has {resp.get('nodes')} nodes")

# ── Status Display ──────────────────────────────────────
def print_status():
    nodes = get_all_nodes()
    print("\n" + "═"*55)
    print(f"  OMEGA MESH STATUS — {THIS_ID}")
    print("═"*55)
    for n in nodes:
        node_id, host, port, status, last_seen, tip, count = n
        icon = "🟢" if status == "active" else "🔴"
        print(f"  {icon} {node_id}")
        print(f"     host={host}:{port} entries={count:,} tip={tip}")
    print("═"*55 + "\n")

# ── Main Loop ───────────────────────────────────────────
def main():
    print(f"\n{'═'*55}")
    print(f"  OMEGA NODE MANAGER v2.0")
    print(f"  Node: {THIS_ID} @ {THIS_HOST}:{MESH_PORT}")
    print(f"{'═'*55}\n")

    ensure_tables()
    register_self()
    announce_to_network()

    # Start mesh TCP server
    t = threading.Thread(target=start_mesh_server, daemon=True)
    t.start()

    gossip_count = 0
    while True:
        try:
            gossip_round()
            gossip_count += 1
            if gossip_count % 3 == 0:
                sync_chain_from_peers()
            if gossip_count % 6 == 0:
                print_status()
        except Exception as e:
            print(f"[MAIN] Error: {e}")
        time.sleep(GOSSIP_INT)

if __name__ == "__main__":
    main()
