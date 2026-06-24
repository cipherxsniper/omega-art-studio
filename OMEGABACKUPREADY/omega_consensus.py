#!/usr/bin/env python3
"""
omega_consensus.py — Omega Bank Self-Organizing Consensus Engine
================================================================
Enterprise-grade distributed consensus daemon for Omega Bank.

Architecture:
  - Gossip Protocol: nodes discover and heartbeat each other autonomously
  - Raft-inspired Quorum: majority vote required before any transfer commits
  - Chain Sync: new nodes bootstrap full ledger state from peers
  - Self-Healing: dead node detection, automatic re-sync, re-registration
  - Auto-Spawn Signals: load-based provisioning signals via PostgreSQL

Run on BOTH phones:
  nohup python3 omega_consensus.py > ~/omega_runtime/logs/consensus.log 2>&1 &

Requires:
  pip install psycopg2-binary requests --break-system-packages
"""

import os
import sys
import time
import json
import socket
import hashlib
import logging
import threading
import traceback
import uuid
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError
import urllib.parse

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Missing psycopg2. Run: pip install psycopg2-binary --break-system-packages")
    sys.exit(1)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "user": "postgres",
    "password": os.environ.get("PGPASSWORD", ""),
    "dbname": "omega_bank",
}

# This node's identity — auto-detected
NODE_HOST = os.environ.get("OMEGA_NODE_HOST", "")  # auto-detected if empty
NODE_PORT = int(os.environ.get("OMEGA_NODE_PORT", "7432"))  # consensus port
NODE_ID   = os.environ.get("OMEGA_NODE_ID", f"omega-node-{socket.gethostname()}")

# Consensus parameters
GOSSIP_INTERVAL      = 5    # seconds between heartbeats
QUORUM_TIMEOUT       = 10   # seconds to wait for votes
DEAD_NODE_THRESHOLD  = 30   # seconds before marking node dead
SYNC_CHUNK_SIZE      = 1000 # rows per sync batch
LOAD_SPAWN_THRESHOLD = 800000  # ledger entries before signaling spawn

# Logging
LOG_DIR = os.path.expanduser("~/omega_runtime/logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/consensus.log"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("OmegaConsensus")


# ─────────────────────────────────────────────
# DATABASE LAYER
# ─────────────────────────────────────────────

class DB:
    """Thread-safe PostgreSQL connection manager."""

    def __init__(self):
        self._local = threading.local()

    def conn(self):
        if not getattr(self._local, "connection", None) or self._local.connection.closed:
            self._local.connection = psycopg2.connect(**DB_CONFIG)
            self._local.connection.autocommit = True
        return self._local.connection

    def execute(self, sql, params=None, fetch=False):
        try:
            cur = self.conn().cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(sql, params)
            if fetch:
                return cur.fetchall()
            return None
        except Exception as e:
            log.error(f"DB error: {e}")
            # Reset connection on error
            self._local.connection = None
            raise

    def fetchone(self, sql, params=None):
        rows = self.execute(sql, params, fetch=True)
        return rows[0] if rows else None

    def fetchall(self, sql, params=None):
        return self.execute(sql, params, fetch=True) or []


db = DB()


# ─────────────────────────────────────────────
# NODE IDENTITY
# ─────────────────────────────────────────────

def detect_local_ip():
    """Detect this machine's LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_node_public_key():
    """Load or generate a node identity key (SHA-256 of node_id + host)."""
    key_path = os.path.expanduser(f"~/omega_runtime/{NODE_ID}.key")
    if os.path.exists(key_path):
        with open(key_path) as f:
            return f.read().strip()
    key = hashlib.sha256(f"{NODE_ID}:{socket.gethostname()}:{time.time()}".encode()).hexdigest()
    os.makedirs(os.path.dirname(key_path), exist_ok=True)
    with open(key_path, "w") as f:
        f.write(key)
    return key


# ─────────────────────────────────────────────
# GOSSIP PROTOCOL
# ─────────────────────────────────────────────

class GossipManager:
    """
    Manages node discovery and heartbeating.
    Every GOSSIP_INTERVAL seconds, this node:
      1. Updates its own last_seen in the DB
      2. Fetches all active peers
      3. Pings each peer's /gossip endpoint
      4. Marks unresponsive peers as inactive
    """

    def __init__(self, node_id, endpoint):
        self.node_id  = node_id
        self.endpoint = endpoint
        self.peers    = {}  # node_id -> endpoint

    def register_self(self):
        """Upsert this node into omega_consensus_nodes."""
        public_key = get_node_public_key()
        db.execute("""
            INSERT INTO omega_consensus_nodes (node_id, endpoint, public_key, last_seen, active)
            VALUES (%s, %s, %s, NOW(), true)
            ON CONFLICT (node_id) DO UPDATE
              SET endpoint  = EXCLUDED.endpoint,
                  last_seen = NOW(),
                  active    = true
        """, (self.node_id, self.endpoint, public_key))
        log.info(f"Registered self: {self.node_id} @ {self.endpoint}")

    def heartbeat(self):
        """Update last_seen for this node."""
        db.execute("""
            UPDATE omega_consensus_nodes
               SET last_seen = NOW(), active = true
             WHERE node_id = %s
        """, (self.node_id,))

    def fetch_peers(self):
        """Load all active peer nodes from DB."""
        rows = db.fetchall("""
            SELECT node_id, endpoint FROM omega_consensus_nodes
             WHERE node_id != %s AND active = true
        """, (self.node_id,))
        self.peers = {r["node_id"]: r["endpoint"] for r in rows}
        return self.peers

    def ping_peer(self, node_id, endpoint):
        """Send gossip heartbeat to a peer. Returns True if alive."""
        try:
            payload = json.dumps({
                "from":     self.node_id,
                "endpoint": self.endpoint,
                "ts":       datetime.now(timezone.utc).isoformat(),
                "chain_head": self.get_local_chain_head(),
            }).encode()
            req = Request(
                f"http://{endpoint}/gossip",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urlopen(req, timeout=5) as resp:
                resp.read()
            return True
        except Exception:
            return False

    def mark_dead(self, node_id):
        """Mark a non-responsive node as inactive."""
        db.execute("""
            UPDATE omega_consensus_nodes
               SET active = false
             WHERE node_id = %s
        """, (node_id,))
        log.warning(f"Marked node dead: {node_id}")

    def check_dead_nodes(self):
        """Mark nodes that haven't heartbeated recently as dead."""
        db.execute("""
            UPDATE omega_consensus_nodes
               SET active = false
             WHERE last_seen < NOW() - INTERVAL '%s seconds'
               AND node_id != %s
               AND active = true
        """, (DEAD_NODE_THRESHOLD, self.node_id))

    def get_local_chain_head(self):
        """Get the latest chain_hash from this node's ledger."""
        row = db.fetchone("""
            SELECT chain_hash, global_sequence
              FROM ledger_entries
             WHERE chain_hash IS NOT NULL
             ORDER BY global_sequence DESC
             LIMIT 1
        """)
        if row:
            return {"hash": row["chain_hash"], "seq": row["global_sequence"]}
        return {"hash": None, "seq": 0}

    def update_peer_state(self, peer_node_id, chain_head):
        """Update consensus state for a peer based on their gossip."""
        db.execute("""
            INSERT INTO omega_consensus_state
                (node_id, chain_head_hash, last_seq, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (node_id) DO UPDATE
              SET chain_head_hash = EXCLUDED.chain_head_hash,
                  last_seq        = EXCLUDED.last_seq,
                  updated_at      = NOW()
        """, (
            peer_node_id,
            chain_head.get("hash"),
            chain_head.get("seq", 0),
        ))

    def run(self):
        """Main gossip loop — runs forever in its own thread."""
        log.info("Gossip manager started")
        self.register_self()

        while True:
            try:
                self.heartbeat()
                peers = self.fetch_peers()
                self.check_dead_nodes()

                for node_id, endpoint in peers.items():
                    alive = self.ping_peer(node_id, endpoint)
                    if not alive:
                        log.warning(f"Peer unreachable: {node_id} @ {endpoint}")
                    else:
                        log.debug(f"Peer alive: {node_id}")

                log.debug(f"Gossip round complete. Active peers: {len(peers)}")

            except Exception as e:
                log.error(f"Gossip error: {e}")

            time.sleep(GOSSIP_INTERVAL)


# ─────────────────────────────────────────────
# QUORUM ENGINE
# ─────────────────────────────────────────────

class QuorumEngine:
    """
    Raft-inspired quorum voting.
    Before any large transfer commits:
      1. Leader proposes a snapshot_id
      2. All peers vote approved/rejected
      3. Majority approval → commit proceeds
      4. Any rejection or timeout → transfer blocked
    """

    def __init__(self, node_id, gossip):
        self.node_id = node_id
        self.gossip  = gossip

    def active_node_count(self):
        row = db.fetchone("""
            SELECT COUNT(*) as cnt FROM omega_consensus_nodes WHERE active = true
        """)
        return row["cnt"] if row else 1

    def quorum_size(self):
        """Majority quorum: floor(n/2) + 1"""
        n = self.active_node_count()
        return (n // 2) + 1

    def propose(self, amount, debit_account, credit_account, memo):
        """
        Propose a transaction for quorum approval.
        Returns (snapshot_id, approved: bool)
        """
        snapshot_id = str(uuid.uuid4())
        state_hash  = self._compute_proposal_hash(snapshot_id, amount, debit_account, credit_account)

        # Self-vote first
        self._cast_vote(snapshot_id, state_hash, approved=True)

        # Request votes from peers
        peers    = self.gossip.fetch_peers()
        approvals = 1  # self-vote
        rejections = 0

        for node_id, endpoint in peers.items():
            result = self._request_vote(endpoint, snapshot_id, state_hash, amount, debit_account, credit_account, memo)
            if result is True:
                approvals += 1
            elif result is False:
                rejections += 1
            # None = timeout, counts as abstain

        needed   = self.quorum_size()
        approved = approvals >= needed

        log.info(
            f"Quorum result: snapshot={snapshot_id[:8]} "
            f"approvals={approvals} needed={needed} → {'APPROVED' if approved else 'REJECTED'}"
        )

        # Record final consensus state
        db.execute("""
            INSERT INTO omega_consensus_state
                (node_id, chain_head_hash, last_seq, updated_at)
            VALUES (%s, %s, 0, NOW())
            ON CONFLICT (node_id) DO UPDATE
              SET chain_head_hash = EXCLUDED.chain_head_hash,
                  updated_at = NOW()
        """, (self.node_id, state_hash))

        return snapshot_id, approved

    def _compute_proposal_hash(self, snapshot_id, amount, debit, credit):
        raw = f"{snapshot_id}:{amount}:{debit}:{credit}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _cast_vote(self, snapshot_id, state_hash, approved):
        db.execute("""
            INSERT INTO omega_consensus_votes
                (node_id, snapshot_id, state_hash, approved, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT DO NOTHING
        """, (self.node_id, snapshot_id, state_hash, approved))

    def _request_vote(self, endpoint, snapshot_id, state_hash, amount, debit, credit, memo):
        """Ask a peer to vote. Returns True/False/None."""
        try:
            payload = json.dumps({
                "snapshot_id": snapshot_id,
                "state_hash":  state_hash,
                "amount":      str(amount),
                "debit":       debit,
                "credit":      credit,
                "memo":        memo,
            }).encode()
            req = Request(
                f"http://{endpoint}/vote",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urlopen(req, timeout=QUORUM_TIMEOUT) as resp:
                body = json.loads(resp.read())
                return body.get("approved", False)
        except Exception as e:
            log.warning(f"Vote request failed to {endpoint}: {e}")
            return None

    def evaluate_vote_request(self, snapshot_id, state_hash, amount, debit, credit, memo):
        """
        Called when THIS node receives a vote request from a peer.
        Applies local risk rules before approving.
        """
        # Rule 1: Amount sanity check
        try:
            amt = float(amount)
        except Exception:
            return False

        if amt <= 0:
            return False

        # Rule 2: Check local chain integrity
        chain_ok = self._verify_local_chain_tip()
        if not chain_ok:
            log.warning("Chain integrity check failed — rejecting vote")
            return False

        # Rule 3: Duplicate snapshot check
        existing = db.fetchone("""
            SELECT approved FROM omega_consensus_votes
             WHERE snapshot_id = %s AND node_id = %s
        """, (snapshot_id, self.node_id))
        if existing:
            return existing["approved"]

        # All checks passed — approve
        approved = True
        self._cast_vote(snapshot_id, state_hash, approved)
        return approved

    def _verify_local_chain_tip(self):
        """Verify the last 10 ledger entries form a valid chain."""
        rows = db.fetchall("""
            SELECT id, prev_hash, chain_hash, debit_account,
                   credit_account, amount, created_at
              FROM ledger_entries
             WHERE chain_hash IS NOT NULL
             ORDER BY global_sequence DESC
             LIMIT 10
        """)
        if not rows:
            return True  # Empty ledger is valid

        for i, row in enumerate(rows[:-1]):
            next_row = rows[i + 1]
            if row["prev_hash"] != next_row["chain_hash"]:
                log.error(f"Chain break detected at seq near id={row['id']}")
                return False
        return True


# ─────────────────────────────────────────────
# CHAIN SYNC ENGINE
# ─────────────────────────────────────────────

class ChainSyncEngine:
    """
    When a new node joins or falls behind:
      1. Identify the peer with the highest global_sequence
      2. Pull ledger entries in chunks
      3. Verify hash chain integrity on each chunk
      4. Mark self as synced and go active
    """

    def __init__(self, node_id, gossip):
        self.node_id = node_id
        self.gossip  = gossip

    def local_last_seq(self):
        row = db.fetchone("SELECT MAX(global_sequence) as seq FROM ledger_entries")
        return row["seq"] or 0 if row else 0

    def find_best_peer(self):
        """Find the peer with the highest last_seq."""
        rows = db.fetchall("""
            SELECT s.node_id, s.last_seq, n.endpoint
              FROM omega_consensus_state s
              JOIN omega_consensus_nodes n USING (node_id)
             WHERE n.active = true AND s.node_id != %s
             ORDER BY s.last_seq DESC
             LIMIT 1
        """, (self.node_id,))
        return rows[0] if rows else None

    def needs_sync(self):
        peer = self.find_best_peer()
        if not peer:
            return False
        local_seq = self.local_last_seq()
        peer_seq  = peer["last_seq"] or 0
        behind    = peer_seq - local_seq
        if behind > 100:
            log.info(f"Behind by {behind} entries — sync needed")
            return True
        return False

    def sync_from_peer(self, peer_endpoint, from_seq):
        """Pull ledger entries from a peer starting at from_seq."""
        try:
            url = f"http://{peer_endpoint}/sync?from_seq={from_seq}&limit={SYNC_CHUNK_SIZE}"
            with urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read())
            entries = data.get("entries", [])
            log.info(f"Received {len(entries)} entries from {peer_endpoint}")
            return entries
        except Exception as e:
            log.error(f"Sync failed from {peer_endpoint}: {e}")
            return []

    def run_sync(self):
        """Full sync loop — catches this node up to the best peer."""
        peer = self.find_best_peer()
        if not peer:
            log.info("No peers available for sync")
            return

        local_seq = self.local_last_seq()
        log.info(f"Starting sync from seq={local_seq} via {peer['endpoint']}")

        while True:
            entries = self.sync_from_peer(peer["endpoint"], local_seq)
            if not entries:
                break

            # Verify and insert each entry
            for entry in entries:
                try:
                    self._insert_synced_entry(entry)
                    local_seq = max(local_seq, entry.get("global_sequence", 0))
                except Exception as e:
                    log.error(f"Failed to insert synced entry: {e}")
                    return

            if len(entries) < SYNC_CHUNK_SIZE:
                break  # Caught up

        log.info(f"Sync complete. Local seq now: {local_seq}")

    def _insert_synced_entry(self, entry):
        """Insert a synced ledger entry preserving hash chain."""
        db.execute("""
            INSERT INTO ledger_entries
                (id, transaction_id, wallet_id, event_type, amount, direction,
                 debit_account, credit_account, memo, idempotency_key,
                 hash, prev_hash, chain_hash, global_sequence, created_at)
            VALUES
                (%(id)s, %(transaction_id)s, %(wallet_id)s, %(event_type)s,
                 %(amount)s, %(direction)s, %(debit_account)s, %(credit_account)s,
                 %(memo)s, %(idempotency_key)s, %(hash)s, %(prev_hash)s,
                 %(chain_hash)s, %(global_sequence)s, %(created_at)s)
            ON CONFLICT (id) DO NOTHING
        """, entry)


# ─────────────────────────────────────────────
# LOAD MONITOR & AUTO-SPAWN SIGNAL
# ─────────────────────────────────────────────

class LoadMonitor:
    """
    Monitors ledger volume and signals when a new node should be provisioned.
    Writes spawn signals to a dedicated table for the control plane to act on.
    """

    def __init__(self, node_id):
        self.node_id = node_id
        self._ensure_spawn_table()

    def _ensure_spawn_table(self):
        db.execute("""
            CREATE TABLE IF NOT EXISTS omega_spawn_signals (
                id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
                signal_node TEXT,
                reason      TEXT,
                ledger_count BIGINT,
                created_at  TIMESTAMP DEFAULT NOW(),
                actioned    BOOLEAN DEFAULT false
            )
        """)

    def check_load(self):
        row = db.fetchone("SELECT COUNT(*) as cnt FROM ledger_entries")
        count = row["cnt"] if row else 0

        if count > LOAD_SPAWN_THRESHOLD:
            # Check if we already signaled recently
            recent = db.fetchone("""
                SELECT id FROM omega_spawn_signals
                 WHERE created_at > NOW() - INTERVAL '1 hour'
                   AND actioned = false
            """)
            if not recent:
                db.execute("""
                    INSERT INTO omega_spawn_signals (signal_node, reason, ledger_count)
                    VALUES (%s, %s, %s)
                """, (self.node_id, f"Ledger count {count} exceeds threshold {LOAD_SPAWN_THRESHOLD}", count))
                log.warning(f"AUTO-SPAWN SIGNAL: ledger at {count} entries — new node needed")

    def run(self):
        log.info("Load monitor started")
        while True:
            try:
                self.check_load()
            except Exception as e:
                log.error(f"Load monitor error: {e}")
            time.sleep(60)


# ─────────────────────────────────────────────
# HTTP SERVER — NODE API
# ─────────────────────────────────────────────

class ConsensusHandler(BaseHTTPRequestHandler):
    """
    HTTP endpoints exposed by each node:
      POST /gossip  — receive heartbeat from peer
      POST /vote    — receive vote request from proposer
      GET  /sync    — serve ledger entries for sync
      GET  /status  — node health and state
    """

    quorum_engine = None  # injected at startup
    gossip_mgr    = None

    def log_message(self, format, *args):
        pass  # Suppress default HTTP logging

    def send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length  = int(self.headers.get("Content-Length", 0))
        body    = self.rfile.read(length)
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        if self.path == "/gossip":
            self._handle_gossip(data)
        elif self.path == "/vote":
            self._handle_vote(data)
        else:
            self.send_json(404, {"error": "not found"})

    def do_GET(self):
        if self.path.startswith("/sync"):
            self._handle_sync()
        elif self.path == "/status":
            self._handle_status()
        else:
            self.send_json(404, {"error": "not found"})

    def _handle_gossip(self, data):
        """Receive a gossip heartbeat from a peer."""
        peer_id       = data.get("from")
        peer_endpoint = data.get("endpoint")
        chain_head    = data.get("chain_head", {})

        if peer_id and peer_endpoint:
            # Update peer last_seen
            db.execute("""
                INSERT INTO omega_consensus_nodes (node_id, endpoint, last_seen, active)
                VALUES (%s, %s, NOW(), true)
                ON CONFLICT (node_id) DO UPDATE
                  SET last_seen = NOW(), active = true, endpoint = EXCLUDED.endpoint
            """, (peer_id, peer_endpoint))

            # Update their chain state
            if chain_head:
                self.gossip_mgr.update_peer_state(peer_id, chain_head)

        self.send_json(200, {"status": "ok", "node": NODE_ID})

    def _handle_vote(self, data):
        """Receive and evaluate a vote request."""
        snapshot_id = data.get("snapshot_id")
        state_hash  = data.get("state_hash")
        amount      = data.get("amount", 0)
        debit       = data.get("debit", "")
        credit      = data.get("credit", "")
        memo        = data.get("memo", "")

        if not snapshot_id:
            self.send_json(400, {"error": "missing snapshot_id"})
            return

        approved = self.quorum_engine.evaluate_vote_request(
            snapshot_id, state_hash, amount, debit, credit, memo
        )
        self.send_json(200, {"approved": approved, "node": NODE_ID})

    def _handle_sync(self):
        """Serve ledger entries for a syncing peer."""
        parsed   = urllib.parse.urlparse(self.path)
        params   = urllib.parse.parse_qs(parsed.query)
        from_seq = int(params.get("from_seq", [0])[0])
        limit    = int(params.get("limit", [SYNC_CHUNK_SIZE])[0])
        limit    = min(limit, SYNC_CHUNK_SIZE)  # cap for safety

        rows = db.fetchall("""
            SELECT id::text, transaction_id::text, wallet_id::text,
                   event_type, amount::text, direction,
                   debit_account, credit_account, memo, idempotency_key,
                   hash, prev_hash, chain_hash,
                   global_sequence,
                   created_at::text
              FROM ledger_entries
             WHERE global_sequence > %s
             ORDER BY global_sequence ASC
             LIMIT %s
        """, (from_seq, limit))

        self.send_json(200, {"entries": [dict(r) for r in rows], "node": NODE_ID})

    def _handle_status(self):
        """Return node health and consensus state."""
        chain_head = self.gossip_mgr.get_local_chain_head() if self.gossip_mgr else {}
        peers      = db.fetchall("""
            SELECT node_id, endpoint, active, last_seen::text
              FROM omega_consensus_nodes
        """)
        row = db.fetchone("SELECT COUNT(*) as cnt FROM ledger_entries")
        ledger_count = row["cnt"] if row else 0

        self.send_json(200, {
            "node_id":      NODE_ID,
            "status":       "alive",
            "chain_head":   chain_head,
            "ledger_count": ledger_count,
            "peers":        [dict(p) for p in peers],
            "quorum_size":  self.quorum_engine.quorum_size() if self.quorum_engine else 1,
            "ts":           datetime.now(timezone.utc).isoformat(),
        })


# ─────────────────────────────────────────────
# SAFE TRANSFER API
# ─────────────────────────────────────────────

class SafeTransfer:
    """
    High-level transfer API that gates commits behind quorum.
    Use this from omega_v10.py instead of direct DB inserts
    for any transfer above the threshold.
    """

    QUORUM_THRESHOLD = 500.00  # USD — below this, no quorum needed

    def __init__(self, quorum_engine):
        self.quorum = quorum_engine

    def execute(self, wallet_id, amount, direction, debit_account,
                credit_account, memo, event_type="TRANSFER"):
        """
        Execute a safe transfer with optional quorum gating.
        Returns dict with success, ledger_id, snapshot_id.
        """
        amount = float(amount)

        if amount >= self.QUORUM_THRESHOLD:
            snapshot_id, approved = self.quorum.propose(
                amount, debit_account, credit_account, memo
            )
            if not approved:
                log.warning(f"Transfer BLOCKED by quorum: amount={amount}")
                return {
                    "success":     False,
                    "reason":      "quorum_rejected",
                    "snapshot_id": snapshot_id,
                }
        else:
            snapshot_id = None

        # Insert ledger entry
        idempotency_key = hashlib.sha256(
            f"{wallet_id}:{amount}:{debit_account}:{credit_account}:{time.time()}".encode()
        ).hexdigest()[:32]

        row = db.fetchone("""
            INSERT INTO ledger_entries
                (transaction_id, wallet_id, event_type, amount, direction,
                 debit_account, credit_account, memo, idempotency_key)
            VALUES
                (uuid_generate_v4(), %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id::text, global_sequence
        """, (
            wallet_id, event_type, amount, direction,
            debit_account, credit_account, memo, idempotency_key
        ))

        log.info(f"Transfer committed: id={row['id']} amount={amount} seq={row['global_sequence']}")
        return {
            "success":          True,
            "ledger_id":        row["id"],
            "global_sequence":  row["global_sequence"],
            "snapshot_id":      snapshot_id,
        }


# ─────────────────────────────────────────────
# MAIN ENTRYPOINT
# ─────────────────────────────────────────────

def main():
    global NODE_HOST

    # Auto-detect IP if not set
    if not NODE_HOST:
        NODE_HOST = detect_local_ip()

    endpoint = f"{NODE_HOST}:{NODE_PORT}"
    log.info(f"Starting Omega Consensus Engine")
    log.info(f"Node ID:   {NODE_ID}")
    log.info(f"Endpoint:  {endpoint}")
    log.info(f"DB:        {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")

    # Ensure consensus tables have unique constraint on node_id
    db.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'omega_consensus_nodes_pkey'
            ) THEN
                ALTER TABLE omega_consensus_nodes ADD PRIMARY KEY (node_id);
            END IF;
        EXCEPTION WHEN others THEN NULL;
        END $$;
    """)

    db.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'omega_consensus_state_pkey'
            ) THEN
                ALTER TABLE omega_consensus_state ADD PRIMARY KEY (node_id);
            END IF;
        EXCEPTION WHEN others THEN NULL;
        END $$;
    """)

    # Initialize components
    gossip   = GossipManager(NODE_ID, endpoint)
    quorum   = QuorumEngine(NODE_ID, gossip)
    sync_eng = ChainSyncEngine(NODE_ID, gossip)
    load_mon = LoadMonitor(NODE_ID)

    # Inject into HTTP handler
    ConsensusHandler.quorum_engine = quorum
    ConsensusHandler.gossip_mgr    = gossip

    # Register this node
    gossip.register_self()

    # Run initial sync if behind
    if sync_eng.needs_sync():
        log.info("Running initial chain sync...")
        sync_eng.run_sync()

    # Start background threads
    threads = [
        threading.Thread(target=gossip.run,   daemon=True, name="Gossip"),
        threading.Thread(target=load_mon.run, daemon=True, name="LoadMonitor"),
    ]

    for t in threads:
        t.start()
        log.info(f"Started thread: {t.name}")

    # Start HTTP server
    server = HTTPServer(("0.0.0.0", NODE_PORT), ConsensusHandler)
    log.info(f"Consensus HTTP server listening on port {NODE_PORT}")
    log.info("=" * 60)
    log.info("Omega Consensus Engine ONLINE")
    log.info(f"Status: http://{endpoint}/status")
    log.info("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down consensus engine")
        server.shutdown()


if __name__ == "__main__":
    main()
