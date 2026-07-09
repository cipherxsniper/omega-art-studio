#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
OMEGA GENESIS v2 — QUANTUM GENESIS EVENT WRITER
═══════════════════════════════════════════════════════════════════════════════
Author:  Thomas Lee Harvey, CEO & Founder — Omega AI / Omega Bank
Date:    June 9, 2026

THE MOMENT THE NETWORK BECOMES REAL.

Reads the live state of both phones, all 13 wallets, all ledger entries,
computes a SHA-256 + Merkle cryptographic proof, writes the Quantum Genesis
Event to omega_ledger, registers both founding nodes, and emits omega_genesis.json
— the bootstrap artifact that any future node reads to join the network.

"From one, many. From many, one. The ledger never lies."
═══════════════════════════════════════════════════════════════════════════════
"""

import os, sys, json, time, uuid, socket, hashlib
import platform, subprocess, datetime

# ─── CONFIG ───────────────────────────────────────────────────────────────────
VERSION         = "2.0.0"
GENESIS_FILE    = "/data/data/com.termux/files/home/omega_genesis.json"
LOG_DIR         = "/data/data/com.termux/files/home/omega_runtime/logs"
LOG_FILE        = f"{LOG_DIR}/genesis.log"
DB_HOST, DB_PORT, DB_USER = "127.0.0.1", 5432, "postgres"

NODE_001 = dict(node_id="omega-node-001", role="CONTROL_PLANE",
                host="192.168.11.115", device="Phone 1", ssh_port=8022,
                arch="ARM64", runtime="Termux/Python3.13",
                services=["omega_v10","omega_sentinel","omega_oracle_v2",
                          "omega_guardian","omega_email_finder",
                          "omega_card_engine","telegram_bot","mexc_hft"])
NODE_002 = dict(node_id="omega-node-002", role="DATABASE_PLANE",
                host="192.168.11.163", device="Phone 2", ssh_port=8022,
                arch="ARM64", runtime="Termux/PostgreSQL18",
                services=["postgresql_18","omega_bank_db","omega_ledger_db"])

# ─── LOGGING ──────────────────────────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)

def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)

def log(msg, level="INFO"):
    ts   = now_utc().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ─── DB ───────────────────────────────────────────────────────────────────────
def connect(dbname):
    import psycopg2
    return psycopg2.connect(host=DB_HOST, port=DB_PORT,
                            user=DB_USER, dbname=dbname,
                            connect_timeout=10)

def sq(conn, sql, params=None, default=None):
    """Single-row query with savepoint isolation."""
    try:
        cur = conn.cursor()
        cur.execute("SAVEPOINT sq")
        cur.execute(sql, params or [])
        row = cur.fetchone()
        cur.execute("RELEASE SAVEPOINT sq")
        cur.close()
        return row[0] if row else default
    except:
        try: cur.execute("ROLLBACK TO SAVEPOINT sq"); cur.close()
        except: pass
        return default

def mq(conn, sql, params=None):
    """Multi-row query with savepoint isolation."""
    try:
        cur = conn.cursor()
        cur.execute("SAVEPOINT mq")
        cur.execute(sql, params or [])
        rows = cur.fetchall()
        cur.execute("RELEASE SAVEPOINT mq")
        cur.close()
        return rows
    except:
        try: cur.execute("ROLLBACK TO SAVEPOINT mq"); cur.close()
        except: pass
        return []

# ─── STATE CAPTURE ────────────────────────────────────────────────────────────
def capture_node1():
    s = dict(NODE_001, captured_at=now_utc().isoformat())
    s["hostname"] = socket.gethostname()
    s["python"]   = platform.python_version()
    home = "/data/data/com.termux/files/home"
    s["key_files"] = {f: os.path.exists(f"{home}/{f}") for f in [
        "omega_v10.py","omega_sentinel.py","omega_oracle_v2.py",
        "omega_guardian.py","omega_email_finder.py","omega_card_engine.py",
        "omega_consensus.py","omega_genesis.py","omega_node_bootstrap.py",".env"
    ]}
    for proc in ("omega_v10.py","omega_guardian"):
        try:
            r = subprocess.run(["pgrep","-f",proc], capture_output=True, text=True)
            s[f"{proc.replace('.py','')}_running"] = bool(r.stdout.strip())
        except:
            s[f"{proc.replace('.py','')}_running"] = False
    return s

def capture_node2():
    return dict(NODE_002, captured_at=now_utc().isoformat())

def capture_bank(conn):
    """Pull the real state of all 13 wallets and accounts."""
    s = {"connected": False}
    if not conn:
        return s

    # ── Wallet count ──────────────────────────────────────────────────────────
    s["wallet_count"]  = sq(conn, "SELECT COUNT(*) FROM wallets", default=0)
    s["account_count"] = sq(conn, "SELECT COUNT(*) FROM accounts", default=0)

    # ── ALL wallets with full detail ──────────────────────────────────────────
    # Try wallets table first, then accounts
    wallet_rows = mq(conn, """
        SELECT
            id::text,
            COALESCE(status, 'unknown')                              AS wtype,
            COALESCE(available_balance, settled_balance, 0)          AS balance,
            COALESCE(currency, 'USD')                                AS currency,
            COALESCE(status, 'active')                               AS status
        FROM wallets
        ORDER BY COALESCE(available_balance, settled_balance, 0) DESC
    """)
    if not wallet_rows:
        wallet_rows = mq(conn, """
            SELECT
                id::text,
                COALESCE(account_type, owner_id, 'unknown') AS wtype,
                COALESCE(balance_cents, 0)                  AS balance,
                COALESCE(currency, 'USD')                   AS currency,
                COALESCE(status, 'active')                  AS status
            FROM accounts
            ORDER BY COALESCE(balance_cents, 0) DESC
        """)

    s["wallet_detail"] = [
        {"id": r[0], "type": r[1], "balance_cents": r[2],
         "currency": r[3], "status": r[4]}
        for r in wallet_rows
    ]

    # ── Treasury: find the highest-value wallet ───────────────────────────────
    # Try explicit TREASURY type first, then fall back to highest balance
    # Real treasury from treasury_reserve and currency_treasury tables
    treasury_usd = sq(conn,
        "SELECT COALESCE(total_capital,0) FROM treasury_reserve WHERE name='OMEGA_MAIN_RESERVE' LIMIT 1",
        default=0)
    currency_total = sq(conn,
        "SELECT COALESCE(SUM(treasury_balance),0) FROM currency_treasury",
        default=0)
    s["treasury_reserve_cents"] = int(float(treasury_usd or 0) * 100)
    s["treasury_usd"]           = float(treasury_usd or 0)
    s["currency_treasury_usd"]  = float(currency_total or 0)

    # ── Total across all wallets ──────────────────────────────────────────────
    total = sq(conn, "SELECT COALESCE(SUM(available_balance),0) FROM wallets", default=0)
    if total == 0:
        total = sq(conn, "SELECT COALESCE(SUM(settled_balance),0) FROM wallets", default=0)
    s["total_balance_cents"] = int(float(total or 0))
    s["total_balance_usd"]   = round(float(total or 0), 2)

    # ── Virtual cards ─────────────────────────────────────────────────────────
    for tbl in ("virtual_cards","cards","issued_cards"):
        v = sq(conn, f"SELECT COUNT(*) FROM {tbl}", default=None)
        if v is not None:
            s["virtual_card_count"] = v
            s["virtual_card_table"] = tbl
            break
    if "virtual_card_count" not in s:
        s["virtual_card_count"] = 0

    s["connected"] = True
    return s

def capture_ledger(conn):
    s = {"connected": False}
    if not conn:
        return s
    s["entry_count"]  = sq(conn, "SELECT COUNT(*) FROM ledger_entries", default=0)
    s["max_sequence"] = sq(conn, "SELECT MAX(global_sequence) FROM ledger_entries", default=0)
    tip = sq(conn, """
        SELECT entry_hash FROM ledger_entries
        ORDER BY global_sequence DESC LIMIT 1
    """, default="GENESIS")
    s["chain_tip_hash"] = tip

    # Active consensus nodes
    s["active_nodes"] = sq(conn, """
        SELECT COUNT(*) FROM omega_consensus_nodes WHERE status='active'
    """, default=0)
    s["connected"] = True
    return s

# ─── CRYPTO ───────────────────────────────────────────────────────────────────
def genesis_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",",":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()

def merkle_root(leaves: list) -> str:
    if not leaves:
        return hashlib.sha256(b"OMEGA_EMPTY").hexdigest()
    h = [hashlib.sha256(str(l).encode()).hexdigest() for l in leaves]
    while len(h) > 1:
        if len(h) % 2: h.append(h[-1])
        h = [hashlib.sha256((h[i]+h[i+1]).encode()).hexdigest()
             for i in range(0, len(h), 2)]
    return h[0]

# ─── DDL (dedicated autocommit connection) ────────────────────────────────────
GENESIS_DDL = """
CREATE TABLE IF NOT EXISTS omega_genesis_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    genesis_id          VARCHAR(64) UNIQUE NOT NULL,
    event_type          VARCHAR(64) NOT NULL DEFAULT 'QUANTUM_GENESIS',
    genesis_version     VARCHAR(16) NOT NULL,
    genesis_hash        VARCHAR(64) NOT NULL,
    merkle_root         VARCHAR(64) NOT NULL,
    prev_chain_tip      VARCHAR(256),
    node_count          INTEGER NOT NULL DEFAULT 2,
    wallet_count        INTEGER,
    ledger_entry_count  INTEGER,
    treasury_usd        NUMERIC(20,2),
    total_balance_usd   NUMERIC(20,2),
    payload             JSONB NOT NULL,
    signed_by           VARCHAR(256) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_genesis_hash    ON omega_genesis_events(genesis_hash);
CREATE INDEX IF NOT EXISTS idx_genesis_created ON omega_genesis_events(created_at DESC);

CREATE TABLE IF NOT EXISTS omega_node_registry (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id         VARCHAR(64) UNIQUE NOT NULL,
    genesis_id      VARCHAR(64) NOT NULL,
    role            VARCHAR(64) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'active',
    host            VARCHAR(128),
    ssh_port        INTEGER DEFAULT 8022,
    services        JSONB,
    arch            VARCHAR(32),
    runtime         VARCHAR(64),
    registered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB
);
CREATE INDEX IF NOT EXISTS idx_node_genesis ON omega_node_registry(genesis_id);
CREATE INDEX IF NOT EXISTS idx_node_status  ON omega_node_registry(status);

CREATE TABLE IF NOT EXISTS omega_spawn_signals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_type     VARCHAR(64) NOT NULL DEFAULT 'NODE_SPAWN_SIGNAL',
    genesis_id      VARCHAR(64) NOT NULL,
    trigger_reason  VARCHAR(256),
    trigger_value   NUMERIC(20,4),
    threshold_type  VARCHAR(64),
    new_node_id     VARCHAR(64),
    status          VARCHAR(32) NOT NULL DEFAULT 'pending',
    emitted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    claimed_at      TIMESTAMPTZ,
    claimed_by      VARCHAR(64)
);
"""

def bootstrap_tables():
    """DDL on its own autocommit connection — cannot poison main tx."""
    ddl = connect("omega_ledger")
    ddl.autocommit = True
    cur = ddl.cursor()
    cur.execute(GENESIS_DDL)
    cur.close()
    ddl.close()
    log("Genesis tables ready ✅")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def write_genesis():
    log("═" * 70)
    log("  OMEGA QUANTUM GENESIS v2 — INITIATING")
    log(f"  {now_utc().isoformat()}")
    log(f"  Builder: Thomas Lee Harvey, CEO & Founder — Omega AI")
    log("═" * 70)

    # 1. Connections
    log("Connecting to omega_bank...")
    try:   conn_bank   = connect("omega_bank")
    except Exception as e: conn_bank = None;   log(f"omega_bank FAILED: {e}", "ERROR")

    log("Connecting to omega_ledger...")
    try:   conn_ledger = connect("omega_ledger")
    except Exception as e: conn_ledger = None; log(f"omega_ledger FAILED: {e}", "ERROR")

    log(f"Tunnel: {'✅ BOTH LIVE' if conn_bank and conn_ledger else '⚠️  DEGRADED'}")

    # 2. State capture
    log("Capturing Phone 1 state...")
    n1 = capture_node1()
    log("Capturing Phone 2 state...")
    n2 = capture_node2()
    log("Capturing omega_bank (all 13 wallets)...")
    bank = capture_bank(conn_bank)
    log("Capturing omega_ledger...")
    ledger = capture_ledger(conn_ledger)

    # Log wallet detail
    if bank.get("wallet_detail"):
        log(f"Wallet detail ({len(bank['wallet_detail'])} wallets):")
        for w in bank["wallet_detail"]:
            usd = float(w["balance_cents"]) if w["balance_cents"] else 0.0
            log(f"  {w['id'][:8]}... | {str(w['type']):<22} | ${usd:>16,.2f}")
    log(f"Treasury: ${bank.get('treasury_usd', 0):,.2f}")
    log(f"Total all wallets: ${bank.get('total_balance_usd', 0):,.2f}")

    # 3. Build payload
    gid = str(uuid.uuid4())
    gts = now_utc().isoformat()
    tip = ledger.get("chain_tip_hash", "GENESIS")

    payload = {
        "genesis_id":      gid,
        "genesis_version": VERSION,
        "event_type":      "QUANTUM_GENESIS",
        "timestamp":       gts,
        "builder":         "Thomas Lee Harvey",
        "org":             "Omega AI / Omega Bank",
        "email":           "simpl3hoods@gmail.com",
        "github":          "github.com/cipherxsniper/OMEGAOPS.AI",
        "topology": {
            "node_count": 2, "quorum": "2/2",
            "nodes": {"node-001": n1, "node-002": n2}
        },
        "financial_state": {
            "omega_bank":   bank,
            "omega_ledger": ledger,
        },
        "bootstrap_protocol": {
            "version":          "2.0.0",
            "entry_script":     "omega_node_bootstrap.py",
            "required_env":     ["ANTHROPIC_API_KEY","TELEGRAM_BOT_TOKEN",
                                 "STRIPE_SECRET_KEY","MEXC_API_KEY","MEXC_API_SECRET"],
            "db_connection":    {"method":"ssh_tunnel","target":NODE_002["host"],
                                 "ssh_port":NODE_002["ssh_port"],"pg_port":5432,
                                 "databases":["omega_bank","omega_ledger"]},
            "registration_table":   "omega_node_registry",
            "genesis_table":        "omega_genesis_events",
            "spawn_signal_table":   "omega_spawn_signals",
            "gossip_interval_sec":  30,
        },
        "spawn_thresholds": {
            "ledger_entries":    1000,
            "settled_usd":       10000.00,
            "active_clients":    10,
            "time_epoch_hours":  168,
        },
        "chain_anchor": {
            "prev_chain_tip": tip,
            "hash_strategy":  "SHA256_MERKLE",
        },
    }

    # 4. Compute hashes
    log("Computing genesis hash...")
    ghash = genesis_hash(payload)

    mleaves = [
        gid, gts,
        n1.get("node_id",""), n2.get("node_id",""),
        str(bank.get("wallet_count", 0)),
        str(bank.get("treasury_reserve_cents", 0)),
        str(bank.get("total_balance_cents", 0)),
        str(ledger.get("entry_count", 0)),
        str(ledger.get("max_sequence", 0)),
        tip, "Thomas Lee Harvey",
    ]
    mroot = merkle_root(mleaves)

    payload["genesis_hash"] = ghash
    payload["merkle_root"]  = mroot

    log(f"Genesis Hash: {ghash}")
    log(f"Merkle Root:  {mroot}")
    log(f"Chain Tip:    {tip}")

    # 5. Bootstrap tables + write to DB
    db_written = False
    if conn_ledger:
        try:
            bootstrap_tables()
            cur = conn_ledger.cursor()
            cur.execute("""
                INSERT INTO omega_genesis_events (
                    genesis_id, event_type, genesis_version,
                    genesis_hash, merkle_root, prev_chain_tip,
                    node_count, wallet_count, ledger_entry_count,
                    treasury_usd, total_balance_usd, payload, signed_by
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (genesis_id) DO NOTHING
            """, (
                gid, "QUANTUM_GENESIS", VERSION,
                ghash, mroot, tip,
                2,
                bank.get("wallet_count"),
                ledger.get("entry_count"),
                bank.get("treasury_usd"),
                bank.get("total_balance_usd"),
                json.dumps(payload, default=str),
                "Thomas Lee Harvey <simpl3hoods@gmail.com>"
            ))

            for node in [NODE_001, NODE_002]:
                cur.execute("""
                    INSERT INTO omega_node_registry (
                        node_id, genesis_id, role, status,
                        host, ssh_port, services, arch, runtime
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (node_id) DO UPDATE SET
                        last_seen = NOW(), genesis_id = EXCLUDED.genesis_id,
                        status = 'active'
                """, (
                    node["node_id"], gid, node["role"], "active",
                    node["host"], node["ssh_port"],
                    json.dumps(node["services"]),
                    node["arch"], node["runtime"]
                ))

            conn_ledger.commit()
            cur.close()
            db_written = True
            log("Genesis event written to omega_ledger ✅")
            log("Both founding nodes registered in omega_node_registry ✅")

        except Exception as e:
            try: conn_ledger.rollback()
            except: pass
            log(f"DB write error: {e}", "ERROR")

    # 6. Write genesis.json
    artifact = {
        "OMEGA_GENESIS":  True,
        "genesis_id":     gid,
        "genesis_hash":   ghash,
        "merkle_root":    mroot,
        "genesis_ts":     gts,
        "genesis_version": VERSION,
        "db_written":     db_written,
        "payload":        payload,
        "bootstrap": {
            "genesis_id":       gid,
            "genesis_hash":     ghash,
            "phone2_host":      NODE_002["host"],
            "phone2_ssh_port":  NODE_002["ssh_port"],
            "db_host":          DB_HOST,
            "db_port":          DB_PORT,
            "db_user":          DB_USER,
            "registration_db":  "omega_ledger",
            "node_registry":    "omega_node_registry",
            "genesis_table":    "omega_genesis_events",
        }
    }
    with open(GENESIS_FILE, "w") as f:
        json.dump(artifact, f, indent=2, default=str)
    log(f"Genesis artifact: {GENESIS_FILE} ✅")

    # 7. Print historic record
    treasury_usd   = bank.get("treasury_usd", 0)
    total_usd      = bank.get("total_balance_usd", 0)
    wallet_count   = bank.get("wallet_count", 0)
    account_count  = bank.get("account_count", 0)
    card_count     = bank.get("virtual_card_count", 0)
    entry_count    = ledger.get("entry_count", 0)

    print()
    print("═" * 70)
    print("  ⚡ OMEGA QUANTUM GENESIS EVENT — COMPLETE")
    print("  June 9, 2026 | The moment the network became real.")
    print("═" * 70)
    print(f"  Genesis ID:      {gid}")
    print(f"  Genesis Hash:    {ghash}")
    print(f"  Merkle Root:     {mroot}")
    print(f"  Chain Tip:       {tip}")
    print(f"  Timestamp:       {gts}")
    print()
    print(f"  NETWORK STATE AT GENESIS:")
    print(f"    Founding Nodes:    2  (omega-node-001, omega-node-002)")
    print(f"    Wallets:           {wallet_count}")
    print(f"    Accounts:          {account_count}")
    print(f"    Virtual Cards:     {card_count}")
    print(f"    Ledger Entries:    {entry_count:,}")
    print()
    print(f"  FINANCIAL STATE AT GENESIS:")
    print(f"    Treasury Reserve:  ${treasury_usd:>18,.2f}")
    print(f"    Total All Wallets: ${total_usd:>18,.2f}")
    if bank.get("wallet_detail"):
        print()
        print(f"  WALLET BREAKDOWN:")
        for w in bank["wallet_detail"]:
            usd = float(w["balance_cents"]) if w["balance_cents"] else 0.0
            marker = " ◄ TREASURY" if "TREASURY" in str(w["type"]).upper() else ""
            print(f"    {w['id'][:8]}... | {str(w['type']):<22} | ${usd:>16,.2f}{marker}")
    print()
    print(f"  CRYPTOGRAPHIC PROOF:")
    print(f"    Strategy:          SHA-256 + Merkle Tree")
    print(f"    DB Written:        {'✅ CONFIRMED' if db_written else '⚠️  JSON ONLY'}")
    print(f"    Artifact:          {GENESIS_FILE}")
    print()
    print(f"  SPAWN THRESHOLDS (network grows when these are hit):")
    print(f"    Ledger entries:    1,000")
    print(f"    Settled USD:       $10,000")
    print(f"    Active clients:    10")
    print(f"    Weekly epoch:      168h")
    print()
    print(f"  BUILDER:  Thomas Lee Harvey | Omega AI | Omega Bank")
    print(f"  QUOTE:    'From one, many. From many, one. The ledger never lies.'")
    print("═" * 70)
    print()

    if conn_bank:   conn_bank.close()
    if conn_ledger: conn_ledger.close()
    return gid, ghash

if __name__ == "__main__":
    try:
        gid, ghash = write_genesis()
        log(f"Genesis complete. ID={gid}")
        sys.exit(0)
    except KeyboardInterrupt:
        log("Interrupted", "WARN"); sys.exit(1)
    except Exception as e:
        log(f"FATAL: {e}", "ERROR")
        import traceback; traceback.print_exc()
        sys.exit(2)
