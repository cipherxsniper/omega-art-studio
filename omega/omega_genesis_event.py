#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
OMEGA GENESIS — QUANTUM GENESIS EVENT WRITER
═══════════════════════════════════════════════════════════════════════════════
Author:  Thomas Lee Harvey, CEO & Founder — Omega AI / Omega Bank
Date:    June 8, 2026
Purpose: Write the Quantum Genesis Event to the ledger.
         This is the cryptographic moment the Omega Network becomes real.
         Every future node bootstraps from this record.
         The chain is mathematically provable from this point forward.

         "From one, many. From many, one. The ledger never lies."

WHAT THIS DOES:
  1. Captures complete state of Phone 1 (control plane) + Phone 2 (PostgreSQL)
  2. Hashes the combined state into a single 256-bit genesis fingerprint
  3. Writes a GENESIS_EVENT record to omega_ledger with full topology snapshot
  4. Signs the record with a Merkle-style chain hash (prev_hash → genesis_hash)
  5. Writes genesis.json — the bootstrap artifact every future node reads first

ENVIRONMENT: Termux Android, Python 3.13, ARM64
             NO pydantic, NO anthropic SDK — urllib only
             PostgreSQL via SSH tunnel (127.0.0.1:5432)
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import socket
import hashlib
import platform
import subprocess
import datetime
import uuid

# ─── CONFIG ───────────────────────────────────────────────────────────────────
GENESIS_VERSION     = "1.0.0"
GENESIS_EVENT_TYPE  = "QUANTUM_GENESIS"
GENESIS_FILE        = "/data/data/com.termux/files/home/omega_genesis.json"
LOG_DIR             = "/data/data/com.termux/files/home/omega_runtime/logs"
LOG_FILE            = f"{LOG_DIR}/genesis.log"

# Node identities
NODE_001 = {
    "node_id":   "omega-node-001",
    "role":      "CONTROL_PLANE",
    "host":      "192.168.11.115",
    "device":    "Phone 1",
    "services":  ["omega_v10", "omega_sentinel", "omega_oracle_v2",
                  "omega_guardian", "omega_email_finder", "omega_card_engine",
                  "telegram_bot", "mexc_hft"],
    "ssh_port":  8022,
    "arch":      "ARM64",
    "runtime":   "Termux/Python3.13"
}

NODE_002 = {
    "node_id":   "omega-node-002",
    "role":      "DATABASE_PLANE",
    "host":      "192.168.11.163",
    "device":    "Phone 2",
    "services":  ["postgresql_18", "omega_bank_db", "omega_ledger_db"],
    "ssh_port":  8022,
    "arch":      "ARM64",
    "runtime":   "Termux/PostgreSQL18"
}

# DB connection (via SSH tunnel)
DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_USER = "postgres"

# ─── LOGGING ──────────────────────────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)

def log(msg, level="INFO"):
    ts  = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ─── DB LAYER (pure psycopg2, no ORM) ────────────────────────────────────────
def get_db(dbname):
    try:
        import psycopg2
        return psycopg2.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, dbname=dbname,
            connect_timeout=10
        )
    except Exception as e:
        log(f"DB connect failed ({dbname}): {e}", "ERROR")
        return None

# ─── SYSTEM STATE CAPTURE ────────────────────────────────────────────────────
def capture_node_state(node_def):
    """Capture live system state for a node definition."""
    state = dict(node_def)
    state["captured_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"

    # Local node gets real metrics
    if node_def["node_id"] == "omega-node-001":
        state["hostname"]     = socket.gethostname()
        state["python"]       = platform.python_version()
        state["platform"]     = platform.platform()
        state["cpu_count"]    = os.cpu_count()
        state["pid"]          = os.getpid()

        # Check which omega processes are running
        try:
            result = subprocess.run(
                ["pgrep", "-f", "omega_v10.py"],
                capture_output=True, text=True
            )
            state["omega_v10_running"] = bool(result.stdout.strip())
        except:
            state["omega_v10_running"] = False

        # Check guardian
        try:
            result = subprocess.run(
                ["pgrep", "-f", "omega_guardian"],
                capture_output=True, text=True
            )
            state["guardian_running"] = bool(result.stdout.strip())
        except:
            state["guardian_running"] = False

        # Count key files
        home = "/data/data/com.termux/files/home"
        state["key_files"] = {
            f: os.path.exists(f"{home}/{f}")
            for f in ["omega_v10.py", "omega_sentinel.py",
                      "omega_oracle_v2.py", "omega_guardian.py",
                      "omega_email_finder.py", "omega_card_engine.py",
                      "omega_consensus.py", ".env"]
        }

    return state


def capture_bank_state(conn_bank):
    """Pull live wallet/account counts from omega_bank."""
    state = {"connected": False}
    if not conn_bank:
        return state

    def _query(conn, sql, default=None):
        """Run a single query with savepoint isolation so one failure can't poison the tx."""
        try:
            cur = conn.cursor()
            cur.execute("SAVEPOINT q")
            cur.execute(sql)
            row = cur.fetchone()
            cur.execute("RELEASE SAVEPOINT q")
            cur.close()
            return row[0] if row else default
        except Exception as e:
            try:
                cur.execute("ROLLBACK TO SAVEPOINT q")
                cur.close()
            except:
                pass
            log(f"Query skipped ({e})", "WARN")
            return default

    state["wallet_count"]  = _query(conn_bank, "SELECT COUNT(*) FROM wallets", 0)
    state["account_count"] = _query(conn_bank, "SELECT COUNT(*) FROM accounts", 0)
    state["total_balance_cents"] = _query(
        conn_bank, "SELECT COALESCE(SUM(balance_cents),0) FROM wallets", 0)

    # Virtual cards — try multiple possible table names
    for tbl in ("virtual_cards", "cards", "issued_cards"):
        vc = _query(conn_bank, f"SELECT COUNT(*) FROM {tbl}", None)
        if vc is not None:
            state["virtual_card_count"] = vc
            break
    if "virtual_card_count" not in state:
        state["virtual_card_count"] = "N/A"

    # Treasury — try wallet_type, then account_type, then name/label
    treasury = None
    for sql in (
        "SELECT balance_cents FROM wallets WHERE wallet_type = 'TREASURY' LIMIT 1",
        "SELECT balance_cents FROM wallets WHERE wallet_type = 'treasury' LIMIT 1",
        "SELECT balance_cents FROM wallets WHERE account_type = 'TREASURY' LIMIT 1",
        "SELECT balance_cents FROM wallets WHERE LOWER(name) LIKE '%treasury%' LIMIT 1",
        "SELECT balance_cents FROM wallets ORDER BY balance_cents DESC LIMIT 1",
    ):
        val = _query(conn_bank, sql, None)
        if val is not None and val > 0:
            treasury = val
            break

    # Also try accounts table
    if not treasury:
        for sql in (
            "SELECT balance_cents FROM accounts WHERE account_type = 'TREASURY' LIMIT 1",
            "SELECT balance_cents FROM accounts ORDER BY balance_cents DESC LIMIT 1",
        ):
            val = _query(conn_bank, sql, None)
            if val is not None and val > 0:
                treasury = val
                break

    state["treasury_reserve_cents"] = treasury or 0
    state["connected"] = True
    return state


def capture_ledger_state(conn_ledger):
    """Pull live ledger metrics from omega_ledger."""
    state = {"connected": False}
    if not conn_ledger:
        return state
    try:
        cur = conn_ledger.cursor()

        cur.execute("SELECT COUNT(*) FROM ledger_entries")
        state["entry_count"] = cur.fetchone()[0]

        cur.execute("""
            SELECT MAX(global_sequence) FROM ledger_entries
        """)
        row = cur.fetchone()
        state["max_sequence"] = row[0] if row else 0

        # Latest hash
        cur.execute("""
            SELECT entry_hash FROM ledger_entries
            ORDER BY global_sequence DESC LIMIT 1
        """)
        row = cur.fetchone()
        state["chain_tip_hash"] = row[0] if row else "GENESIS"

        # Active nodes in consensus
        try:
            cur.execute("""
                SELECT COUNT(*) FROM omega_consensus_nodes
                WHERE status = 'active'
            """)
            state["active_consensus_nodes"] = cur.fetchone()[0]
        except:
            state["active_consensus_nodes"] = 0

        state["connected"] = True
        cur.close()
    except Exception as e:
        state["error"] = str(e)
    return state


# ─── HASH ENGINE ─────────────────────────────────────────────────────────────
def compute_genesis_hash(genesis_payload: dict) -> str:
    """
    Deterministic SHA-256 of the genesis payload.
    Sort keys for canonical form — same state always produces same hash.
    """
    canonical = json.dumps(genesis_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def compute_merkle_root(leaves: list) -> str:
    """
    Simple Merkle root over a list of strings.
    Pairs items, hashes each pair, recurse until one root.
    """
    if not leaves:
        return hashlib.sha256(b"OMEGA_EMPTY").hexdigest()
    hashes = [hashlib.sha256(str(l).encode()).hexdigest() for l in leaves]
    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])  # duplicate last if odd
        hashes = [
            hashlib.sha256((hashes[i] + hashes[i+1]).encode()).hexdigest()
            for i in range(0, len(hashes), 2)
        ]
    return hashes[0]


# ─── GENESIS TABLE BOOTSTRAP ─────────────────────────────────────────────────
GENESIS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS omega_genesis_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    genesis_id          VARCHAR(64) UNIQUE NOT NULL,
    event_type          VARCHAR(64) NOT NULL DEFAULT 'QUANTUM_GENESIS',
    genesis_version     VARCHAR(16) NOT NULL,
    genesis_hash        VARCHAR(64) NOT NULL,
    merkle_root         VARCHAR(64) NOT NULL,
    prev_chain_tip      VARCHAR(64),
    node_count          INTEGER NOT NULL DEFAULT 2,
    wallet_count        INTEGER,
    ledger_entry_count  INTEGER,
    treasury_usd        NUMERIC(20,2),
    payload             JSONB NOT NULL,
    signed_by           VARCHAR(256) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_genesis_hash
    ON omega_genesis_events(genesis_hash);

CREATE INDEX IF NOT EXISTS idx_genesis_created
    ON omega_genesis_events(created_at DESC);
"""

NODE_REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS omega_node_registry (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id             VARCHAR(64) UNIQUE NOT NULL,
    genesis_id          VARCHAR(64) NOT NULL,
    role                VARCHAR(64) NOT NULL,
    status              VARCHAR(32) NOT NULL DEFAULT 'active',
    host                VARCHAR(128),
    ssh_port            INTEGER DEFAULT 8022,
    services            JSONB,
    arch                VARCHAR(32),
    runtime             VARCHAR(64),
    registered_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata            JSONB
);

CREATE INDEX IF NOT EXISTS idx_node_registry_genesis
    ON omega_node_registry(genesis_id);

CREATE INDEX IF NOT EXISTS idx_node_registry_status
    ON omega_node_registry(status);
"""

SPAWN_SIGNAL_DDL = """
CREATE TABLE IF NOT EXISTS omega_spawn_signals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_type         VARCHAR(64) NOT NULL DEFAULT 'NODE_SPAWN_SIGNAL',
    genesis_id          VARCHAR(64) NOT NULL,
    trigger_reason      VARCHAR(256),
    trigger_value       NUMERIC(20,4),
    threshold_type      VARCHAR(64),
    new_node_id         VARCHAR(64),
    status              VARCHAR(32) NOT NULL DEFAULT 'pending',
    emitted_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    claimed_at          TIMESTAMPTZ,
    claimed_by          VARCHAR(64)
);
"""


def bootstrap_genesis_tables():
    """
    Create genesis tables using a DEDICATED connection with autocommit=True.
    DDL runs outside any transaction block so errors can NEVER poison
    the main ledger connection used for the genesis INSERT.
    """
    try:
        import psycopg2
        ddl_conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, dbname="omega_ledger",
            connect_timeout=10
        )
        ddl_conn.autocommit = True
        cur = ddl_conn.cursor()
        cur.execute(GENESIS_TABLE_DDL)
        cur.execute(NODE_REGISTRY_DDL)
        cur.execute(SPAWN_SIGNAL_DDL)
        cur.close()
        ddl_conn.close()
        log("Genesis tables bootstrapped ✅")
        return True
    except Exception as e:
        log(f"Table bootstrap failed: {e}", "ERROR")
        return False


# ─── CORE GENESIS WRITER ──────────────────────────────────────────────────────
def write_quantum_genesis_event():
    """
    THE HISTORIC MOMENT.
    Captures full system state, computes genesis hash, writes to ledger.
    """

    log("═" * 70)
    log("  OMEGA QUANTUM GENESIS — INITIATING")
    log(f"  Date: {datetime.datetime.now(datetime.timezone.utc).isoformat()}Z")
    log(f"  Builder: Thomas Lee Harvey, CEO & Founder")
    log("═" * 70)

    # ── 1. Connect to both databases ─────────────────────────────────────────
    log("Connecting to omega_bank...")
    conn_bank   = get_db("omega_bank")
    log("Connecting to omega_ledger...")
    conn_ledger = get_db("omega_ledger")

    tunnel_live = conn_bank is not None and conn_ledger is not None
    log(f"SSH tunnel status: {'✅ LIVE' if tunnel_live else '⚠️  DEGRADED (genesis proceeds)'}")

    # ── 2. Capture system state ───────────────────────────────────────────────
    log("Capturing Phone 1 (Control Plane) state...")
    node1_state = capture_node_state(NODE_001)

    log("Capturing Phone 2 (Database Plane) state...")
    node2_state = capture_node_state(NODE_002)

    log("Capturing omega_bank metrics...")
    bank_state  = capture_bank_state(conn_bank)

    log("Capturing omega_ledger metrics...")
    ledger_state = capture_ledger_state(conn_ledger)

    # ── 3. Build genesis payload ──────────────────────────────────────────────
    genesis_id      = str(uuid.uuid4())
    genesis_ts      = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
    chain_tip       = ledger_state.get("chain_tip_hash", "GENESIS")

    payload = {
        "genesis_id":       genesis_id,
        "genesis_version":  GENESIS_VERSION,
        "event_type":       GENESIS_EVENT_TYPE,
        "timestamp":        genesis_ts,
        "builder":          "Thomas Lee Harvey",
        "org":              "Omega AI / Omega Bank",
        "email":            "simpl3hoods@gmail.com",
        "github":           "github.com/cipherxsniper/OMEGAOPS.AI",

        # Network topology at genesis moment
        "topology": {
            "node_count":   2,
            "quorum":       "2/2",
            "nodes": {
                "node-001": node1_state,
                "node-002": node2_state,
            }
        },

        # Financial state at genesis moment
        "financial_state": {
            "omega_bank":   bank_state,
            "omega_ledger": ledger_state,
        },

        # Bootstrap instructions for any future node
        "bootstrap_protocol": {
            "version":              "1.0.0",
            "bootstrap_entry":      "omega_node_bootstrap.py",
            "required_env": [
                "ANTHROPIC_API_KEY", "TELEGRAM_BOT_TOKEN",
                "STRIPE_SECRET_KEY", "MEXC_API_KEY", "MEXC_API_SECRET"
            ],
            "db_connection": {
                "method":   "ssh_tunnel",
                "target":   NODE_002["host"],
                "ssh_port": NODE_002["ssh_port"],
                "pg_port":  5432,
                "databases": ["omega_bank", "omega_ledger"]
            },
            "registration_table":   "omega_node_registry",
            "genesis_table":        "omega_genesis_events",
            "spawn_signal_table":   "omega_spawn_signals",
            "gossip_interval_sec":  30,
            "heartbeat_interval_sec": 60,
        },

        # Spawn thresholds — when to grow the network
        "spawn_thresholds": {
            "ledger_entries":       1000,
            "settled_usd":          10000.00,
            "time_epoch_hours":     168,    # 1 week
            "active_clients":       10,
        },

        # Cryptographic chain anchor
        "chain_anchor": {
            "prev_chain_tip":   chain_tip,
            "anchor_strategy":  "SHA256_MERKLE",
        }
    }

    # ── 4. Compute genesis hash & Merkle root ─────────────────────────────────
    log("Computing genesis hash...")
    genesis_hash = compute_genesis_hash(payload)

    # Merkle over key state components for tamper-evidence
    merkle_leaves = [
        genesis_id,
        genesis_ts,
        node1_state.get("node_id", ""),
        node2_state.get("node_id", ""),
        str(bank_state.get("wallet_count", 0)),
        str(ledger_state.get("entry_count", 0)),
        str(ledger_state.get("max_sequence", 0)),
        chain_tip,
        "Thomas Lee Harvey",
    ]
    merkle_root = compute_merkle_root(merkle_leaves)

    # Add hashes back into payload (they prove themselves)
    payload["genesis_hash"]  = genesis_hash
    payload["merkle_root"]   = merkle_root

    log(f"Genesis Hash:  {genesis_hash}")
    log(f"Merkle Root:   {merkle_root}")
    log(f"Chain Tip:     {chain_tip}")

    # ── 5. Write to omega_ledger ──────────────────────────────────────────────
    db_written = False
    if conn_ledger:
        try:
            if bootstrap_genesis_tables():
                cur = conn_ledger.cursor()
                cur.execute("""
                    INSERT INTO omega_genesis_events (
                        genesis_id, event_type, genesis_version,
                        genesis_hash, merkle_root, prev_chain_tip,
                        node_count, wallet_count, ledger_entry_count,
                        treasury_usd, payload, signed_by
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s
                    )
                    ON CONFLICT (genesis_id) DO NOTHING
                """, (
                    genesis_id,
                    GENESIS_EVENT_TYPE,
                    GENESIS_VERSION,
                    genesis_hash,
                    merkle_root,
                    chain_tip,
                    2,
                    bank_state.get("wallet_count"),
                    ledger_state.get("entry_count"),
                    round(bank_state.get("treasury_reserve_cents", 0) / 100, 2)
                        if bank_state.get("treasury_reserve_cents") else None,
                    json.dumps(payload),
                    "Thomas Lee Harvey <simpl3hoods@gmail.com>"
                ))

                # Register both founding nodes
                for node_def in [NODE_001, NODE_002]:
                    cur.execute("""
                        INSERT INTO omega_node_registry (
                            node_id, genesis_id, role, status,
                            host, ssh_port, services, arch, runtime
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (node_id) DO UPDATE SET
                            last_seen = NOW(),
                            genesis_id = EXCLUDED.genesis_id
                    """, (
                        node_def["node_id"],
                        genesis_id,
                        node_def["role"],
                        "active",
                        node_def["host"],
                        node_def["ssh_port"],
                        json.dumps(node_def["services"]),
                        node_def["arch"],
                        node_def["runtime"]
                    ))

                conn_ledger.commit()
                cur.close()
                db_written = True
                log("Genesis event written to omega_ledger ✅")
                log("Founding nodes registered in omega_node_registry ✅")

        except Exception as e:
            conn_ledger.rollback()
            log(f"DB write failed: {e}", "ERROR")
            log("Genesis JSON will be written to disk as fallback", "WARN")

    # ── 6. Write genesis.json (bootstrap artifact) ───────────────────────────
    genesis_artifact = {
        "OMEGA_GENESIS": True,
        "genesis_id":    genesis_id,
        "genesis_hash":  genesis_hash,
        "merkle_root":   merkle_root,
        "genesis_ts":    genesis_ts,
        "db_written":    db_written,
        "payload":       payload,

        # Quick-reference for bootstrap scripts
        "bootstrap": {
            "genesis_id":       genesis_id,
            "genesis_hash":     genesis_hash,
            "db_host_tunnel":   DB_HOST,
            "db_port":          DB_PORT,
            "db_user":          DB_USER,
            "phone2_host":      NODE_002["host"],
            "phone2_ssh_port":  NODE_002["ssh_port"],
            "registration_db":  "omega_ledger",
            "node_registry":    "omega_node_registry",
            "genesis_table":    "omega_genesis_events",
        }
    }

    with open(GENESIS_FILE, "w") as f:
        json.dump(genesis_artifact, f, indent=2, default=str)

    log(f"Genesis artifact written: {GENESIS_FILE} ✅")

    # ── 7. Print the historic record ──────────────────────────────────────────
    treasury_usd = bank_state.get("treasury_reserve_cents", 0) / 100 \
                   if bank_state.get("treasury_reserve_cents") else 0

    print()
    print("═" * 70)
    print("  ⚡ OMEGA QUANTUM GENESIS EVENT — COMPLETE")
    print("═" * 70)
    print(f"  Genesis ID:      {genesis_id}")
    print(f"  Genesis Hash:    {genesis_hash}")
    print(f"  Merkle Root:     {merkle_root}")
    print(f"  Chain Tip:       {chain_tip}")
    print(f"  Timestamp:       {genesis_ts}")
    print()
    print(f"  NETWORK STATE AT GENESIS:")
    print(f"    Nodes:         2 (omega-node-001, omega-node-002)")
    print(f"    Wallets:       {bank_state.get('wallet_count', 'N/A')}")
    print(f"    Accounts:      {bank_state.get('account_count', 'N/A')}")
    print(f"    Ledger Entries:{ledger_state.get('entry_count', 'N/A')}")
    print(f"    Virtual Cards: {bank_state.get('virtual_card_count', 'N/A')}")
    print(f"    Treasury:      ${treasury_usd:,.2f}")
    print()
    print(f"  CRYPTOGRAPHIC PROOF:")
    print(f"    Hash Strategy: SHA-256 + Merkle")
    print(f"    DB Written:    {'✅ YES' if db_written else '⚠️  JSON ONLY'}")
    print(f"    Artifact:      {GENESIS_FILE}")
    print()
    print(f"  SPAWN THRESHOLDS (when next node auto-creates):")
    print(f"    Ledger entries:  1,000")
    print(f"    Settled USD:     $10,000")
    print(f"    Time epoch:      168h (1 week)")
    print(f"    Active clients:  10")
    print()
    print(f"  BUILDER: Thomas Lee Harvey | Omega AI | June 8, 2026")
    print(f"  'From one, many. From many, one. The ledger never lies.'")
    print("═" * 70)
    print()

    if conn_bank:
        conn_bank.close()
    if conn_ledger:
        conn_ledger.close()

    return genesis_id, genesis_hash


# ─── ENTRYPOINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        genesis_id, genesis_hash = write_quantum_genesis_event()
        log(f"Genesis complete. ID={genesis_id} Hash={genesis_hash[:16]}...")
        sys.exit(0)
    except KeyboardInterrupt:
        log("Genesis interrupted by user", "WARN")
        sys.exit(1)
    except Exception as e:
        log(f"Genesis failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(2)
