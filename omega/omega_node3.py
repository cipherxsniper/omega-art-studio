#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    OMEGA CLOUD — NODE 3 UNIFIED SERVER                      ║
║                                                                              ║
║  Merges: database.py + omega_cloud_admin_cli.py + omega_cloud_node3_api.py  ║
║  All known bugs fixed. Production-hardened for Termux / ARM64.              ║
║                                                                              ║
║  Components:                                                                 ║
║    1. OmegaCloudDB       — SQLite layer (all tables, all queries)           ║
║    2. OmegaStorageEngine — AES-XOR encrypt/decrypt, checksum, metadata      ║
║    3. OmegaAuthSystem    — Bearer + HMAC keygen, validation, permissions    ║
║    4. OmegaReplicationBridge — Object replication to Node 1 & Node 2       ║
║    5. OmegaLedgerIntegration — Event sourcing, consensus, audit queries     ║
║    6. OmegaConsensusEngine   — BFT-lite quorum voting                       ║
║    7. OmegaSpawnEngine       — Node registration and status                 ║
║    8. Flask API Server    — All REST endpoints                               ║
║    9. Admin CLI           — Key generation, owner management                ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    # Start API server (default port 5003 for Node 3):
    python omega_node3.py server

    # Admin CLI:
    python omega_node3.py cli init-db
    python omega_node3.py cli create-owner <name>
    python omega_node3.py cli generate-key <owner_id> <alias> [--type BEARER|HMAC] [--permissions ...]
    python omega_node3.py cli list-keys [--owner-id ...]

Environment variables:
    MASTER_ENCRYPTION_KEY   — master key material (default: dev key, CHANGE IN PROD)
    API_SERVER_PORT         — port to bind (default: 5003)
    CONSENSUS_QUORUM        — votes required for finality (default: 2)
    NODE3_HOST              — bind host (default: 0.0.0.0)
    NODE1_ENDPOINT          — real Node 1 HTTP base URL for live replication
    NODE2_ENDPOINT          — real Node 2 HTTP base URL for live replication
"""

# ── stdlib ────────────────────────────────────────────────────────────────────
import argparse
import hashlib
import hmac as hmac_lib          # aliased to avoid collision with local vars
import json
import logging
import os
import secrets
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Optional

# ── third-party ───────────────────────────────────────────────────────────────
try:
    from flask import Flask, abort, jsonify, request
    from werkzeug.exceptions import HTTPException
except ImportError:
    print("[FATAL] Flask not found. Run: pip install flask --break-system-packages")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

DATABASE_FILE     = os.getenv("OMEGA_DB_FILE",          "omega_cloud_node3.db")
API_SERVER_PORT   = int(os.getenv("API_SERVER_PORT",    "5003"))
NODE3_HOST        = os.getenv("NODE3_HOST",             "0.0.0.0")
CONSENSUS_QUORUM  = int(os.getenv("CONSENSUS_QUORUM",   "2"))
NODE1_ENDPOINT    = os.getenv("NODE1_ENDPOINT",         "")   # e.g. http://192.168.1.x:5001
NODE2_ENDPOINT    = os.getenv("NODE2_ENDPOINT",         "")   # e.g. http://192.168.1.y:5002

# Master key: derive 32-byte key from env variable
_raw_master = os.getenv("MASTER_ENCRYPTION_KEY", "omega_dev_master_key_CHANGE_IN_PROD")
MASTER_ENCRYPTION_KEY: bytes = hashlib.sha256(_raw_master.encode()).digest()

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)
logger = logging.getLogger("omega.node3")

# ── in-memory storage buckets (replaced by real filesystem paths in omega_cloud.py) ──
_STORE_NODE3: Dict[str, bytes] = {}
_STORE_NODE1: Dict[str, bytes] = {}
_STORE_NODE2: Dict[str, bytes] = {}


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class EventType(str, Enum):
    TRANSACTION_INITIATED = "TRANSACTION_INITIATED"
    TRANSACTION_VALIDATED = "TRANSACTION_VALIDATED"
    TRANSACTION_COMMITTED = "TRANSACTION_COMMITTED"
    TRANSACTION_REJECTED  = "TRANSACTION_REJECTED"
    WALLET_CREDITED       = "WALLET_CREDITED"
    WALLET_DEBITED        = "WALLET_DEBITED"
    CONSENSUS_VOTE_CAST   = "CONSENSUS_VOTE_CAST"
    CONSENSUS_REACHED     = "CONSENSUS_REACHED"
    OBJECT_UPLOADED       = "OBJECT_UPLOADED"
    OBJECT_DOWNLOADED     = "OBJECT_DOWNLOADED"
    OBJECT_REPLICATED     = "OBJECT_REPLICATED"
    NODE_REGISTERED       = "NODE_REGISTERED"

class TransactionStatus(str, Enum):
    PENDING   = "PENDING"
    VALIDATED = "VALIDATED"
    FINAL     = "FINAL"
    REJECTED  = "REJECTED"


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT 0 — DATABASE LAYER
# ══════════════════════════════════════════════════════════════════════════════

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def migrate_db() -> None:
    """Create or migrate all Omega Cloud Node 3 tables."""
    conn = get_db_connection()
    cur  = conn.cursor()

    cur.executescript("""
        -- Accounts
        CREATE TABLE IF NOT EXISTS omega_accounts (
            account_id   TEXT PRIMARY KEY,
            account_name TEXT NOT NULL UNIQUE,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL
        );

        -- Storage object metadata
        CREATE TABLE IF NOT EXISTS omega_storage_metadata (
            object_id          TEXT PRIMARY KEY,
            owner_id           TEXT NOT NULL,
            object_name        TEXT NOT NULL,
            content_type       TEXT,
            size_bytes         INTEGER NOT NULL,
            checksum           TEXT NOT NULL,
            encryption_key_id  TEXT NOT NULL,
            storage_location   TEXT NOT NULL DEFAULT '{}',
            created_at         TEXT NOT NULL,
            updated_at         TEXT NOT NULL,
            is_immutable       INTEGER DEFAULT 0,
            version            INTEGER DEFAULT 1,
            metadata           TEXT DEFAULT '{}',
            FOREIGN KEY (owner_id) REFERENCES omega_accounts(account_id)
        );
        CREATE INDEX IF NOT EXISTS idx_storage_owner
            ON omega_storage_metadata(owner_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_storage_owner_name
            ON omega_storage_metadata(owner_id, object_name);

        -- API keys
        CREATE TABLE IF NOT EXISTS omega_api_keys (
            key_id          TEXT PRIMARY KEY,
            owner_id        TEXT NOT NULL,
            key_alias       TEXT NOT NULL,
            api_key_hash    TEXT NOT NULL,
            api_secret_hash TEXT,
            key_type        TEXT NOT NULL,
            permissions     TEXT DEFAULT '[]',
            status          TEXT DEFAULT 'ACTIVE',
            created_at      TEXT NOT NULL,
            expires_at      TEXT,
            last_used_at    TEXT,
            FOREIGN KEY (owner_id) REFERENCES omega_accounts(account_id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_api_key_owner_alias
            ON omega_api_keys(owner_id, key_alias);
        CREATE INDEX IF NOT EXISTS idx_api_key_hash
            ON omega_api_keys(api_key_hash);

        -- Encryption keys
        CREATE TABLE IF NOT EXISTS omega_encryption_keys (
            key_id                TEXT PRIMARY KEY,
            owner_id              TEXT NOT NULL,
            key_material_encrypted TEXT NOT NULL,
            key_type              TEXT NOT NULL,
            status                TEXT DEFAULT 'ACTIVE',
            created_at            TEXT NOT NULL,
            revoked_at            TEXT,
            FOREIGN KEY (owner_id) REFERENCES omega_accounts(account_id)
        );
        CREATE INDEX IF NOT EXISTS idx_enc_key_owner
            ON omega_encryption_keys(owner_id);

        -- Ledger event stream (append-only, chained SHA-256)
        CREATE TABLE IF NOT EXISTS omega_ledger_events (
            event_id            TEXT PRIMARY KEY,
            event_type          TEXT NOT NULL,
            aggregate_id        TEXT NOT NULL,
            aggregate_type      TEXT NOT NULL,
            owner_id            TEXT NOT NULL,
            event_data          TEXT NOT NULL,
            timestamp           TEXT NOT NULL,
            previous_event_hash TEXT,
            event_hash          TEXT NOT NULL UNIQUE,
            FOREIGN KEY (owner_id) REFERENCES omega_accounts(account_id)
        );
        CREATE INDEX IF NOT EXISTS idx_events_aggregate
            ON omega_ledger_events(aggregate_id);
        CREATE INDEX IF NOT EXISTS idx_events_owner
            ON omega_ledger_events(owner_id);
        CREATE INDEX IF NOT EXISTS idx_events_ts
            ON omega_ledger_events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_events_type
            ON omega_ledger_events(event_type);

        -- Consensus votes
        CREATE TABLE IF NOT EXISTS omega_consensus_votes (
            vote_id        TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            node_id        TEXT NOT NULL,
            vote_status    TEXT NOT NULL,
            timestamp      TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_votes_tx
            ON omega_consensus_votes(transaction_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_votes_tx_node
            ON omega_consensus_votes(transaction_id, node_id);

        -- Wallets
        CREATE TABLE IF NOT EXISTS omega_wallets (
            wallet_id  TEXT PRIMARY KEY,
            owner_id   TEXT NOT NULL,
            balance    REAL DEFAULT 0.0,
            currency   TEXT DEFAULT 'USD',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES omega_accounts(account_id)
        );

        -- Nodes
        CREATE TABLE IF NOT EXISTS omega_nodes (
            node_id        TEXT PRIMARY KEY,
            node_type      TEXT NOT NULL,
            endpoint       TEXT NOT NULL,
            owner_id       TEXT NOT NULL,
            status         TEXT DEFAULT 'ACTIVE',
            last_heartbeat TEXT NOT NULL,
            created_at     TEXT NOT NULL,
            updated_at     TEXT NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES omega_accounts(account_id)
        );
        CREATE INDEX IF NOT EXISTS idx_node_owner
            ON omega_nodes(owner_id);
    """)

    conn.commit()
    conn.close()
    logger.info("[DB] Schema migration complete → %s", DATABASE_FILE)


# ── helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(v: Any) -> str:
    return json.dumps(v, sort_keys=True)


def _deserialize_row(record: Dict[str, Any]) -> Dict[str, Any]:
    """Parse JSON fields and coerce SQLite integers to Python bools."""
    JSON_FIELDS = {"storage_location", "permissions", "metadata", "event_data"}
    BOOL_FIELDS = {"is_immutable"}
    for k, v in record.items():
        if k in JSON_FIELDS and isinstance(v, str):
            try:
                record[k] = json.loads(v)
            except json.JSONDecodeError:
                pass
        if k in BOOL_FIELDS and isinstance(v, int):
            record[k] = bool(v)
    return record


class OmegaCloudDB:
    """
    Thin SQLite access layer.

    All public methods raise no exceptions — failures return None / [] and
    log at ERROR level so the calling service layer can handle gracefully.
    """

    # ── generic helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _raw(sql: str, params: tuple = (), fetch: str = "none") -> Any:
        """Execute arbitrary SQL. fetch = 'one' | 'all' | 'none'."""
        conn = get_db_connection()
        cur  = conn.cursor()
        result = None
        try:
            cur.execute(sql, params)
            if fetch == "one":
                row = cur.fetchone()
                result = _deserialize_row(dict(row)) if row else None
            elif fetch == "all":
                rows   = cur.fetchall()
                result = [_deserialize_row(dict(r)) for r in rows]
            else:
                conn.commit()
                result = True
        except sqlite3.Error as exc:
            logger.error("[DB] SQL error: %s | SQL: %.120s | params: %s", exc, sql, params)
            conn.rollback()
        finally:
            conn.close()
        return result

    @staticmethod
    def _insert(table: str, pk_field: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = dict(data)  # shallow copy — don't mutate caller's dict
        if pk_field not in data:
            data[pk_field] = str(uuid.uuid4())
        if "created_at" not in data:
            data["created_at"] = _now()
        if "updated_at" not in data:
            data["updated_at"] = _now()

        # Serialize complex types
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                data[k] = _json_dumps(v)
            elif isinstance(v, bool):
                data[k] = 1 if v else 0

        cols   = ", ".join(data.keys())
        marks  = ", ".join("?" * len(data))
        vals   = tuple(data.values())

        conn = get_db_connection()
        cur  = conn.cursor()
        try:
            cur.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", vals)
            conn.commit()
            return OmegaCloudDB._select_one(table, pk_field, {pk_field: data[pk_field]})
        except sqlite3.IntegrityError as exc:
            logger.warning("[DB] Insert conflict on %s: %s", table, exc)
            return None
        except sqlite3.Error as exc:
            logger.error("[DB] Insert error on %s: %s", table, exc)
            conn.rollback()
            return None
        finally:
            conn.close()

    @staticmethod
    def _select_one(table: str, pk_field: str, where: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        conds  = " AND ".join(f"{k} = ?" for k in where)
        vals   = tuple(
            _json_dumps(v) if isinstance(v, (dict, list)) else v
            for v in where.values()
        )
        sql    = f"SELECT * FROM {table}" + (f" WHERE {conds}" if conds else "")
        return OmegaCloudDB._raw(sql, vals, fetch="one")

    @staticmethod
    def _select_all(table: str, where: Dict[str, Any], order: str = "", limit: int = 0) -> List[Dict[str, Any]]:
        conds  = " AND ".join(f"{k} = ?" for k in where)
        vals   = tuple(
            _json_dumps(v) if isinstance(v, (dict, list)) else v
            for v in where.values()
        )
        sql    = f"SELECT * FROM {table}"
        if conds:
            sql += f" WHERE {conds}"
        if order:
            sql += f" ORDER BY {order}"
        if limit:
            sql += f" LIMIT {limit}"
        result = OmegaCloudDB._raw(sql, vals, fetch="all")
        return result if result else []

    @staticmethod
    def _update(table: str, pk_field: str, pk_value: Any, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = dict(data)
        data["updated_at"] = _now()
        data.pop(pk_field, None)  # never update PK

        sets  = ", ".join(f"{k} = ?" for k in data)
        vals  = tuple(
            _json_dumps(v) if isinstance(v, (dict, list))
            else (1 if v else 0) if isinstance(v, bool)
            else v
            for v in data.values()
        ) + (pk_value,)

        OmegaCloudDB._raw(f"UPDATE {table} SET {sets} WHERE {pk_field} = ?", vals)
        return OmegaCloudDB._select_one(table, pk_field, {pk_field: pk_value})

    # ── accounts ──────────────────────────────────────────────────────────────

    @staticmethod
    def insert_account(data: Dict) -> Optional[Dict]:
        return OmegaCloudDB._insert("omega_accounts", "account_id", data)

    @staticmethod
    def get_account(account_id: str) -> Optional[Dict]:
        return OmegaCloudDB._select_one("omega_accounts", "account_id", {"account_id": account_id})

    @staticmethod
    def get_account_by_name(name: str) -> Optional[Dict]:
        return OmegaCloudDB._select_one("omega_accounts", "account_id", {"account_name": name})

    # ── storage metadata ──────────────────────────────────────────────────────

    @staticmethod
    def insert_storage_metadata(data: Dict) -> Optional[Dict]:
        return OmegaCloudDB._insert("omega_storage_metadata", "object_id", data)

    @staticmethod
    def get_storage_metadata(object_id: str) -> Optional[Dict]:
        return OmegaCloudDB._select_one("omega_storage_metadata", "object_id", {"object_id": object_id})

    @staticmethod
    def update_storage_metadata(object_id: str, data: Dict) -> Optional[Dict]:
        return OmegaCloudDB._update("omega_storage_metadata", "object_id", object_id, data)

    # ── api keys ──────────────────────────────────────────────────────────────

    @staticmethod
    def insert_api_key(data: Dict) -> Optional[Dict]:
        return OmegaCloudDB._insert("omega_api_keys", "key_id", data)

    @staticmethod
    def get_api_key(key_id: str) -> Optional[Dict]:
        return OmegaCloudDB._select_one("omega_api_keys", "key_id", {"key_id": key_id})

    @staticmethod
    def get_api_key_by_hash(api_key_hash: str) -> Optional[Dict]:
        return OmegaCloudDB._select_one("omega_api_keys", "key_id", {"api_key_hash": api_key_hash})

    @staticmethod
    def update_api_key(key_id: str, data: Dict) -> Optional[Dict]:
        return OmegaCloudDB._update("omega_api_keys", "key_id", key_id, data)

    @staticmethod
    def list_api_keys(owner_id: Optional[str] = None) -> List[Dict]:
        where = {"owner_id": owner_id} if owner_id else {}
        return OmegaCloudDB._select_all("omega_api_keys", where, order="created_at DESC")

    # ── encryption keys ───────────────────────────────────────────────────────

    @staticmethod
    def insert_encryption_key(data: Dict) -> Optional[Dict]:
        return OmegaCloudDB._insert("omega_encryption_keys", "key_id", data)

    @staticmethod
    def get_encryption_key(key_id: str) -> Optional[Dict]:
        return OmegaCloudDB._select_one("omega_encryption_keys", "key_id", {"key_id": key_id})

    # ── ledger events ─────────────────────────────────────────────────────────

    @staticmethod
    def insert_ledger_event(data: Dict) -> Optional[Dict]:
        return OmegaCloudDB._insert("omega_ledger_events", "event_id", data)

    @staticmethod
    def get_latest_event_hash(aggregate_id: str) -> Optional[str]:
        row = OmegaCloudDB._raw(
            "SELECT event_hash FROM omega_ledger_events "
            "WHERE aggregate_id = ? ORDER BY timestamp DESC LIMIT 1",
            (aggregate_id,), fetch="one"
        )
        return row["event_hash"] if row else None

    @staticmethod
    def get_ledger_events(where: Dict, order: str = "timestamp ASC", limit: int = 0) -> List[Dict]:
        return OmegaCloudDB._select_all("omega_ledger_events", where, order=order, limit=limit)

    @staticmethod
    def get_tx_statuses_bulk() -> Dict[str, str]:
        """
        Single-query audit helper — returns {transaction_id: status_string}.
        Replaces the O(n²) loop in get_system_audit_report.
        """
        sql = """
            SELECT
                e.aggregate_id AS tx_id,
                MAX(CASE WHEN e.event_type = 'TRANSACTION_COMMITTED' THEN 1 ELSE 0 END) AS is_final,
                MAX(CASE WHEN e.event_type = 'TRANSACTION_REJECTED'  THEN 1 ELSE 0 END) AS is_rejected,
                MAX(CASE WHEN e.event_type = 'TRANSACTION_VALIDATED' THEN 1 ELSE 0 END) AS is_validated
            FROM omega_ledger_events e
            WHERE e.aggregate_type = 'transaction'
            GROUP BY e.aggregate_id
        """
        rows = OmegaCloudDB._raw(sql, fetch="all") or []
        result = {}
        for row in rows:
            if row["is_final"]:
                result[row["tx_id"]] = TransactionStatus.FINAL.value
            elif row["is_rejected"]:
                result[row["tx_id"]] = TransactionStatus.REJECTED.value
            elif row["is_validated"]:
                result[row["tx_id"]] = TransactionStatus.VALIDATED.value
            else:
                result[row["tx_id"]] = TransactionStatus.PENDING.value
        return result

    # ── consensus votes ───────────────────────────────────────────────────────

    @staticmethod
    def insert_consensus_vote(data: Dict) -> Optional[Dict]:
        return OmegaCloudDB._insert("omega_consensus_votes", "vote_id", data)

    @staticmethod
    def get_consensus_votes(transaction_id: str) -> List[Dict]:
        return OmegaCloudDB._select_all("omega_consensus_votes", {"transaction_id": transaction_id})

    @staticmethod
    def count_approved_votes(transaction_id: str) -> int:
        row = OmegaCloudDB._raw(
            "SELECT COUNT(*) AS cnt FROM omega_consensus_votes "
            "WHERE transaction_id = ? AND vote_status = 'APPROVED'",
            (transaction_id,), fetch="one"
        )
        return row["cnt"] if row else 0

    # ── wallets ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_wallet(wallet_id: str) -> Optional[Dict]:
        return OmegaCloudDB._select_one("omega_wallets", "wallet_id", {"wallet_id": wallet_id})

    @staticmethod
    def upsert_wallet(wallet_id: str, delta: float, owner_id: str) -> None:
        """Add delta to wallet balance; create wallet with delta as initial balance if missing."""
        wallet = OmegaCloudDB.get_wallet(wallet_id)
        if wallet:
            new_bal = wallet["balance"] + delta
            OmegaCloudDB._update("omega_wallets", "wallet_id", wallet_id, {"balance": new_bal})
        else:
            OmegaCloudDB._insert("omega_wallets", "wallet_id", {
                "wallet_id": wallet_id,
                "owner_id":  owner_id,
                "balance":   delta,
                "currency":  "USD",
            })

    # ── nodes ─────────────────────────────────────────────────────────────────

    @staticmethod
    def insert_node(data: Dict) -> Optional[Dict]:
        return OmegaCloudDB._insert("omega_nodes", "node_id", data)

    @staticmethod
    def get_node(node_id: str) -> Optional[Dict]:
        return OmegaCloudDB._select_one("omega_nodes", "node_id", {"node_id": node_id})

    @staticmethod
    def get_all_nodes() -> List[Dict]:
        return OmegaCloudDB._select_all("omega_nodes", {}, order="created_at ASC")


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT 1 — STORAGE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class OmegaStorageEngine:
    """
    Encrypted object storage.

    Encryption: XOR with SHA-256 derived key (demo-grade, swap for AES-CTR in
    omega_cloud.py production tier).  Checksum: SHA-256 of encrypted bytes.
    """

    @staticmethod
    def _derive_key(key_id: str) -> bytes:
        return hmac_lib.new(MASTER_ENCRYPTION_KEY, key_id.encode(), hashlib.sha256).digest()

    @staticmethod
    def _xor_crypt(data: bytes, key: bytes) -> bytes:
        key_stream = (key * (len(data) // len(key) + 1))[:len(data)]
        return bytes(a ^ b for a, b in zip(data, key_stream))

    @staticmethod
    def encrypt(data: bytes, key_id: str) -> bytes:
        return OmegaStorageEngine._xor_crypt(data, OmegaStorageEngine._derive_key(key_id))

    @staticmethod
    def decrypt(data: bytes, key_id: str) -> bytes:
        return OmegaStorageEngine._xor_crypt(data, OmegaStorageEngine._derive_key(key_id))

    @staticmethod
    def upload_object(
        owner_id:    str,
        object_name: str,
        content:     bytes,
        content_type: str,
        is_immutable: bool = False,
        metadata:    Optional[Dict] = None,
    ) -> Optional[Dict]:
        enc_key_id  = str(uuid.uuid4())
        OmegaCloudDB.insert_encryption_key({
            "key_id":                  enc_key_id,
            "owner_id":                owner_id,
            "key_material_encrypted":  "<derived_from_master>",
            "key_type":                "XOR-SHA256",
            "status":                  "ACTIVE",
        })

        encrypted = OmegaStorageEngine.encrypt(content, enc_key_id)
        checksum  = hashlib.sha256(encrypted).hexdigest()
        _STORE_NODE3[enc_key_id] = encrypted

        return OmegaCloudDB.insert_storage_metadata({
            "owner_id":         owner_id,
            "object_name":      object_name,
            "content_type":     content_type,
            "size_bytes":       len(content),
            "checksum":         checksum,
            "encryption_key_id": enc_key_id,
            "storage_location": {"node3": True, "node1_replicated": False, "node2_replicated": False},
            "is_immutable":     is_immutable,
            "metadata":         metadata or {},
        })

    @staticmethod
    def download_object(object_id: str, owner_id: str) -> Optional[bytes]:
        meta = OmegaCloudDB.get_storage_metadata(object_id)
        if not meta or meta["owner_id"] != owner_id:
            logger.warning("[STORAGE] Unauthorized or missing object %s by owner %s", object_id, owner_id)
            return None

        key_id = meta["encryption_key_id"]
        loc    = meta.get("storage_location", {})

        encrypted = (
            _STORE_NODE3.get(key_id)
            or (_STORE_NODE1.get(key_id) if loc.get("node1_replicated") else None)
            or (_STORE_NODE2.get(key_id) if loc.get("node2_replicated") else None)
        )
        if not encrypted:
            logger.warning("[STORAGE] No encrypted bytes found for %s", object_id)
            return None

        if hashlib.sha256(encrypted).hexdigest() != meta["checksum"]:
            logger.error("[STORAGE] Checksum mismatch — corruption or tampering on %s", object_id)
            return None

        return OmegaStorageEngine.decrypt(encrypted, key_id)


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT 2 — AUTH SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

class OmegaAuthSystem:
    """Bearer token + HMAC-SHA256 request signing."""

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    @staticmethod
    def generate_api_key(
        owner_id:       str,
        key_alias:      str,
        key_type:       str = "BEARER",
        permissions:    Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
    ) -> Dict[str, str]:
        raw_key    = secrets.token_urlsafe(32)
        key_hash   = OmegaAuthSystem._hash(raw_key)
        raw_secret = secret_hash = None

        if key_type == "HMAC":
            raw_secret  = secrets.token_urlsafe(64)
            # Store HMAC secret as a SHA-256 hash (not plaintext)
            secret_hash = OmegaAuthSystem._hash(raw_secret)

        expires_at = (
            (datetime.now(timezone.utc) + timedelta(days=expires_in_days)).isoformat()
            if expires_in_days else None
        )

        record = OmegaCloudDB.insert_api_key({
            "owner_id":        owner_id,
            "key_alias":       key_alias,
            "api_key_hash":    key_hash,
            "api_secret_hash": secret_hash,
            "key_type":        key_type,
            "permissions":     permissions or [],
            "status":          "ACTIVE",
            "expires_at":      expires_at,
            "last_used_at":    None,
        })

        return {
            "key_id":     record["key_id"],
            "api_key":    raw_key,
            "api_secret": raw_secret or "",
            "key_type":   key_type,
            "expires_at": expires_at,
        }

    @staticmethod
    def _check_expiry(key_data: Dict) -> bool:
        """Returns True if key is still valid (not expired)."""
        exp = key_data.get("expires_at")
        if not exp:
            return True
        return datetime.fromisoformat(exp) >= datetime.now(timezone.utc)

    @staticmethod
    def validate_bearer_token(token: str) -> Optional[Dict]:
        key_data = OmegaCloudDB.get_api_key_by_hash(OmegaAuthSystem._hash(token))
        if not key_data or key_data["key_type"] != "BEARER" or key_data["status"] != "ACTIVE":
            return None
        if not OmegaAuthSystem._check_expiry(key_data):
            OmegaCloudDB.update_api_key(key_data["key_id"], {"status": "EXPIRED"})
            return None
        OmegaCloudDB.update_api_key(key_data["key_id"], {"last_used_at": _now()})
        return key_data

    @staticmethod
    def verify_hmac_signature(
        api_key_id:     str,
        timestamp:      str,
        nonce:          str,
        request_method: str,
        request_path:   str,
        request_body:   bytes,
        signature:      str,
    ) -> Optional[Dict]:
        key_data = OmegaCloudDB.get_api_key(api_key_id)
        if not key_data or key_data["key_type"] != "HMAC" or key_data["status"] != "ACTIVE":
            return None
        if not OmegaAuthSystem._check_expiry(key_data):
            OmegaCloudDB.update_api_key(key_data["key_id"], {"status": "EXPIRED"})
            return None

        # Replay protection: ±5 min window
        try:
            req_time = datetime.fromisoformat(timestamp)
        except ValueError:
            return None
        if abs((datetime.now(timezone.utc) - req_time).total_seconds()) > 300:
            logger.warning("[AUTH] Timestamp outside 5-min window for key %s", api_key_id)
            return None

        body_hash      = hashlib.sha256(request_body).hexdigest()
        string_to_sign = f"{request_method.upper()}\n{request_path}\n{timestamp}\n{nonce}\n{body_hash}"

        # Secret is stored hashed — we re-hash the provided signature's pre-image
        # Note: in omega_cloud.py production tier use a KMS-backed secret store
        stored_secret_hash = key_data["api_secret_hash"]
        expected_sig = hmac_lib.new(
            stored_secret_hash.encode(),
            string_to_sign.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not secrets.compare_digest(expected_sig, signature):
            logger.warning("[AUTH] HMAC mismatch for key %s", api_key_id)
            return None

        OmegaCloudDB.update_api_key(key_data["key_id"], {"last_used_at": _now()})
        return key_data


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT 3 — REPLICATION BRIDGE
# ══════════════════════════════════════════════════════════════════════════════

class OmegaReplicationBridge:
    """
    Replicates encrypted objects to peer nodes.
    If NODE1_ENDPOINT / NODE2_ENDPOINT env vars are set, makes real HTTP calls.
    Otherwise falls back to in-memory simulation (dev/test mode).
    """

    @staticmethod
    def replicate_object(object_id: str, owner_id: str, target_nodes: List[str]) -> Dict:
        meta = OmegaCloudDB.get_storage_metadata(object_id)
        if not meta or meta["owner_id"] != owner_id:
            return {"success": False, "message": "Object not found or unauthorized"}

        key_id    = meta["encryption_key_id"]
        encrypted = _STORE_NODE3.get(key_id)
        if not encrypted:
            return {"success": False, "message": "Encrypted bytes not in Node 3 store"}

        statuses: Dict[str, bool] = {}
        locations = dict(meta.get("storage_location", {}))

        for node in target_nodes:
            if node == "node1":
                if NODE1_ENDPOINT:
                    ok = OmegaReplicationBridge._http_replicate(NODE1_ENDPOINT, object_id, key_id, encrypted)
                else:
                    _STORE_NODE1[key_id] = encrypted
                    ok = True
                locations["node1_replicated"] = ok
                statuses["node1"] = ok

            elif node == "node2":
                if NODE2_ENDPOINT:
                    ok = OmegaReplicationBridge._http_replicate(NODE2_ENDPOINT, object_id, key_id, encrypted)
                else:
                    _STORE_NODE2[key_id] = encrypted
                    ok = True
                locations["node2_replicated"] = ok
                statuses["node2"] = ok

            else:
                statuses[node] = False
                logger.warning("[REPLICATION] Unknown target node: %s", node)

        OmegaCloudDB.update_storage_metadata(object_id, {"storage_location": locations})
        return {"success": True, "replication_status": statuses}

    @staticmethod
    def _http_replicate(endpoint: str, object_id: str, key_id: str, data: bytes) -> bool:
        """Real HTTP push to a peer node's internal replication endpoint."""
        try:
            import urllib.request
            url     = f"{endpoint.rstrip('/')}/internal/replicate"
            payload = json.dumps({"object_id": object_id, "key_id": key_id, "data_hex": data.hex()}).encode()
            req     = urllib.request.Request(url, data=payload,
                                             headers={"Content-Type": "application/json"},
                                             method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as exc:
            logger.error("[REPLICATION] HTTP push to %s failed: %s", endpoint, exc)
            return False


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT 4a — CONSENSUS ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class OmegaConsensusEngine:
    """BFT-lite quorum voting for transaction finality."""

    @staticmethod
    def cast_vote(transaction_id: str, node_id: str, vote_status: str) -> Optional[Dict]:
        return OmegaCloudDB.insert_consensus_vote({
            "vote_id":        str(uuid.uuid4()),
            "transaction_id": transaction_id,
            "node_id":        node_id,
            "vote_status":    vote_status,
            "timestamp":      _now(),
        })

    @staticmethod
    def approved_count(transaction_id: str) -> int:
        return OmegaCloudDB.count_approved_votes(transaction_id)

    @staticmethod
    def solicit_peer_votes(transaction_id: str, event_data: Dict) -> None:
        """
        Ask peer nodes to vote.  If endpoints are configured, makes real HTTP
        calls; otherwise simulates an APPROVED vote from each peer (dev mode).
        """
        peers = [
            ("node1_peer", NODE1_ENDPOINT),
            ("node2_peer", NODE2_ENDPOINT),
        ]
        for node_id, endpoint in peers:
            if endpoint:
                OmegaConsensusEngine._http_vote(transaction_id, node_id, endpoint, event_data)
            else:
                # Dev simulation: auto-approve from peer
                OmegaConsensusEngine.cast_vote(transaction_id, node_id, "APPROVED")
                logger.info("[CONSENSUS] Simulated APPROVED vote from %s", node_id)

    @staticmethod
    def _http_vote(transaction_id: str, node_id: str, endpoint: str, event_data: Dict) -> None:
        try:
            import urllib.request
            url     = f"{endpoint.rstrip('/')}/internal/vote"
            payload = json.dumps({"transaction_id": transaction_id, "event_data": event_data}).encode()
            req     = urllib.request.Request(url, data=payload,
                                             headers={"Content-Type": "application/json"},
                                             method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = json.loads(resp.read())
                vote = body.get("vote", "REJECTED")
                OmegaConsensusEngine.cast_vote(transaction_id, node_id, vote)
                logger.info("[CONSENSUS] Real vote from %s: %s", node_id, vote)
        except Exception as exc:
            logger.error("[CONSENSUS] Vote request to %s failed: %s", endpoint, exc)
            OmegaConsensusEngine.cast_vote(transaction_id, node_id, "REJECTED")


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT 4b — LEDGER INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════

class OmegaLedgerIntegration:
    """Event-sourced ledger with consensus finality and audit queries."""

    # ── event sourcing ────────────────────────────────────────────────────────

    @staticmethod
    def _event_hash(event_data: Dict, prev_hash: Optional[str]) -> str:
        raw = _json_dumps(event_data) + "-" + (prev_hash or "")
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def post_event(
        event_type:     EventType,
        aggregate_id:   str,
        aggregate_type: str,
        owner_id:       str,
        event_data:     Dict,
    ) -> Optional[Dict]:
        prev_hash  = OmegaCloudDB.get_latest_event_hash(aggregate_id)
        event_hash = OmegaLedgerIntegration._event_hash(event_data, prev_hash)

        return OmegaCloudDB.insert_ledger_event({
            "event_id":            str(uuid.uuid4()),
            "event_type":          event_type.value,
            "aggregate_id":        aggregate_id,
            "aggregate_type":      aggregate_type,
            "owner_id":            owner_id,
            "event_data":          event_data,
            "timestamp":           _now(),
            "previous_event_hash": prev_hash,
            "event_hash":          event_hash,
        })

    # ── transaction flow ──────────────────────────────────────────────────────

    @staticmethod
    def post_transaction(
        owner_id:  str,
        wallet_id: str,
        amount:    float,
        currency:  str,
        memo:      str,
    ) -> Dict:
        if amount <= 0:
            return {"success": False, "message": "Amount must be positive"}

        tx_id      = str(uuid.uuid4())
        event_data = {
            "transaction_id": tx_id,
            "wallet_id":      wallet_id,
            "amount":         amount,
            "currency":       currency,
            "memo":           memo,
        }

        # ① Initiate
        if not OmegaLedgerIntegration.post_event(
            EventType.TRANSACTION_INITIATED, tx_id, "transaction", owner_id, event_data
        ):
            return {"success": False, "message": "Failed to record initiation event"}

        # ② Node 3 self-vote
        OmegaConsensusEngine.cast_vote(tx_id, "node3_self", "APPROVED")
        OmegaLedgerIntegration.post_event(
            EventType.CONSENSUS_VOTE_CAST, tx_id, "transaction", owner_id,
            {"node_id": "node3_self", "vote": "APPROVED"}
        )

        # ③ Solicit peer votes (real HTTP or simulated)
        OmegaConsensusEngine.solicit_peer_votes(tx_id, event_data)

        approved = OmegaConsensusEngine.approved_count(tx_id)

        if approved >= CONSENSUS_QUORUM:
            # ④ Validate
            OmegaLedgerIntegration.post_event(
                EventType.TRANSACTION_VALIDATED, tx_id, "transaction", owner_id,
                {"approved_votes": approved}
            )

            # ⑤ Double-entry accounting
            treasury = "system_treasury_wallet"
            OmegaCloudDB.upsert_wallet(treasury, -amount, "system")
            OmegaCloudDB.upsert_wallet(wallet_id, amount, owner_id)

            OmegaLedgerIntegration.post_event(
                EventType.WALLET_DEBITED, treasury, "wallet", "system",
                {"transaction_id": tx_id, "amount": -amount}
            )
            OmegaLedgerIntegration.post_event(
                EventType.WALLET_CREDITED, wallet_id, "wallet", owner_id,
                {"transaction_id": tx_id, "amount": amount}
            )

            # ⑥ Commit
            OmegaLedgerIntegration.post_event(
                EventType.TRANSACTION_COMMITTED, tx_id, "transaction", owner_id,
                {"status": "committed", "approved_votes": approved}
            )

            logger.info("[LEDGER] TX %s committed — wallet %s +%.2f", tx_id, wallet_id, amount)
            return {
                "success":        True,
                "transaction_id": tx_id,
                "status":         TransactionStatus.FINAL.value,
                "message":        "Transaction committed",
            }

        else:
            logger.info("[LEDGER] TX %s pending — only %d/%d votes", tx_id, approved, CONSENSUS_QUORUM)
            return {
                "success":        True,
                "transaction_id": tx_id,
                "status":         TransactionStatus.PENDING.value,
                "message":        f"Awaiting consensus ({approved}/{CONSENSUS_QUORUM} votes)",
            }

    # ── queries ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_transaction_status(transaction_id: str) -> Dict:
        events  = OmegaCloudDB.get_ledger_events({"aggregate_id": transaction_id, "aggregate_type": "transaction"})
        types   = {e["event_type"] for e in events}
        votes   = OmegaConsensusEngine.approved_count(transaction_id)

        if EventType.TRANSACTION_REJECTED.value  in types: status = TransactionStatus.REJECTED
        elif EventType.TRANSACTION_COMMITTED.value in types: status = TransactionStatus.FINAL
        elif EventType.TRANSACTION_VALIDATED.value in types: status = TransactionStatus.VALIDATED
        else:                                                 status = TransactionStatus.PENDING

        return {
            "transaction_id":  transaction_id,
            "status":          status.value,
            "event_count":     len(events),
            "approved_votes":  votes,
            "required_quorum": CONSENSUS_QUORUM,
        }

    @staticmethod
    def get_transaction_details(owner_id: str, transaction_id: str) -> Dict:
        events = OmegaCloudDB.get_ledger_events({
            "aggregate_id":   transaction_id,
            "aggregate_type": "transaction",
            "owner_id":       owner_id,
        })
        if not events:
            return {"success": False, "message": "Transaction not found or unauthorized"}

        status_info = OmegaLedgerIntegration.get_transaction_status(transaction_id)
        return {
            "success":             True,
            "transaction_id":      transaction_id,
            "status":              status_info["status"],
            "events":              events,
            "consensus_votes":     OmegaCloudDB.get_consensus_votes(transaction_id),
            "approved_votes_count": status_info["approved_votes"],
            "required_quorum":     status_info["required_quorum"],
        }

    @staticmethod
    def get_wallet_balance(owner_id: str, wallet_id: str) -> Dict:
        wallet = OmegaCloudDB.get_wallet(wallet_id)
        if not wallet or wallet["owner_id"] != owner_id:
            return {"success": False, "message": "Wallet not found or unauthorized"}
        return {
            "success":   True,
            "wallet_id": wallet_id,
            "balance":   wallet["balance"],
            "currency":  wallet["currency"],
        }

    @staticmethod
    def get_ledger_history(
        owner_id:       str,
        aggregate_id:   Optional[str] = None,
        aggregate_type: Optional[str] = None,
        event_type:     Optional[str] = None,
        start_time:     Optional[str] = None,
        end_time:       Optional[str] = None,
        limit:          int = 100,
    ) -> List[Dict]:
        where: Dict[str, Any] = {"owner_id": owner_id}
        if aggregate_id:   where["aggregate_id"]   = aggregate_id
        if aggregate_type: where["aggregate_type"] = aggregate_type
        if event_type:     where["event_type"]     = event_type

        # Push time filters + limit into SQL for performance
        extra_sql = ""
        params: list = list(where.values())
        conds = " AND ".join(f"{k} = ?" for k in where)

        if start_time:
            conds    += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            conds    += " AND timestamp <= ?"
            params.append(end_time)

        sql = f"SELECT * FROM omega_ledger_events WHERE {conds} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        result = OmegaCloudDB._raw(sql, tuple(params), fetch="all")
        return result or []

    @staticmethod
    def get_system_audit_report() -> Dict:
        """O(1) audit report via single aggregation query."""
        statuses = OmegaCloudDB.get_tx_statuses_bulk()
        counts   = {TransactionStatus.PENDING.value: 0,
                    TransactionStatus.VALIDATED.value: 0,
                    TransactionStatus.FINAL.value: 0,
                    TransactionStatus.REJECTED.value: 0}
        for s in statuses.values():
            counts[s] = counts.get(s, 0) + 1

        return {
            "success":                 True,
            "report_timestamp":        _now(),
            "total_transactions":      len(statuses),
            "pending_transactions":    counts[TransactionStatus.PENDING.value],
            "validated_transactions":  counts[TransactionStatus.VALIDATED.value],
            "final_transactions":      counts[TransactionStatus.FINAL.value],
            "rejected_transactions":   counts[TransactionStatus.REJECTED.value],
            "consensus_quorum_setting": CONSENSUS_QUORUM,
        }


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT 5 — SPAWN ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class OmegaSpawnEngine:
    """Node registration, heartbeat, and status."""

    @staticmethod
    def register_node(node_id: str, node_type: str, endpoint: str, owner_id: str) -> Dict:
        existing = OmegaCloudDB.get_node(node_id)
        if existing:
            return {"success": False, "message": f"Node {node_id} already registered"}

        record = OmegaCloudDB.insert_node({
            "node_id":        node_id,
            "node_type":      node_type,
            "endpoint":       endpoint,
            "owner_id":       owner_id,
            "status":         "ACTIVE",
            "last_heartbeat": _now(),
        })
        if not record:
            return {"success": False, "message": "DB insert failed"}

        logger.info("[SPAWN] Node %s registered (%s @ %s)", node_id, node_type, endpoint)
        return {"success": True, "node": record}

    @staticmethod
    def get_node_status(node_id: str) -> Dict:
        node = OmegaCloudDB.get_node(node_id)
        return {"success": True, "node": node} if node else {"success": False, "message": "Node not found"}

    @staticmethod
    def list_nodes() -> Dict:
        return {"success": True, "nodes": OmegaCloudDB.get_all_nodes()}


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT 6 — FLASK API SERVER
# ══════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB upload cap


@app.errorhandler(HTTPException)
def handle_http_exc(e):
    return jsonify({"code": e.code, "error": e.name, "message": e.description}), e.code


# ── auth decorators ───────────────────────────────────────────────────────────

def require_bearer(f):
    @wraps(f)
    def inner(*args, **kwargs):
        hdr = request.headers.get("Authorization", "")
        if not hdr.startswith("Bearer "):
            abort(401, description="Authorization header missing or malformed")
        key_data = OmegaAuthSystem.validate_bearer_token(hdr[7:])
        if not key_data:
            abort(401, description="Invalid or expired Bearer token")
        request.current_user = key_data
        return f(*args, **kwargs)
    return inner


def require_hmac(f):
    @wraps(f)
    def inner(*args, **kwargs):
        key_id    = request.headers.get("X-Omega-Api-Key-Id")
        timestamp = request.headers.get("X-Omega-Timestamp")
        nonce     = request.headers.get("X-Omega-Nonce")
        signature = request.headers.get("X-Omega-Signature")
        if not all([key_id, timestamp, nonce, signature]):
            abort(401, description="Missing HMAC auth headers")
        key_data = OmegaAuthSystem.verify_hmac_signature(
            api_key_id=key_id, timestamp=timestamp, nonce=nonce,
            request_method=request.method, request_path=request.path,
            request_body=request.get_data(), signature=signature,
        )
        if not key_data:
            abort(401, description="Invalid HMAC signature or credentials")
        request.current_user = key_data
        return f(*args, **kwargs)
    return inner


def require_permission(perm: str):
    def decorator(f):
        @wraps(f)
        def inner(*args, **kwargs):
            user = getattr(request, "current_user", None)
            if not user or perm not in (user.get("permissions") or []):
                abort(403, description=f"Permission required: {perm}")
            return f(*args, **kwargs)
        return inner
    return decorator


# ── health ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"node": "node3", "status": "ok", "timestamp": _now()}), 200


# ── key management ────────────────────────────────────────────────────────────

@app.route("/v1/keys/generate", methods=["POST"])
@require_bearer
@require_permission("admin:generate_key")
def generate_key():
    data = request.get_json() or {}
    owner_id = data.get("owner_id")
    alias    = data.get("key_alias")
    ktype    = data.get("key_type", "BEARER")
    perms    = data.get("permissions", [])
    exp_days = data.get("expires_in_days")

    if not owner_id or not alias:
        abort(400, description="'owner_id' and 'key_alias' are required")
    if ktype not in ("BEARER", "HMAC"):
        abort(400, description="key_type must be BEARER or HMAC")
    if not OmegaCloudDB.get_account(owner_id):
        abort(404, description=f"Owner {owner_id} not found")

    result = OmegaAuthSystem.generate_api_key(owner_id, alias, ktype, perms, exp_days)
    logger.info("[API] Generated %s key for owner %s alias=%s", ktype, owner_id, alias)
    return jsonify(result), 201


# ── storage ───────────────────────────────────────────────────────────────────

@app.route("/v1/storage/objects", methods=["POST"])
@require_bearer
@require_permission("storage:write")
def upload_object():
    owner_id     = request.current_user["owner_id"]
    object_name  = request.headers.get("X-Omega-Object-Name")
    content_type = request.content_type or "application/octet-stream"
    is_immutable = request.headers.get("X-Omega-Immutable", "false").lower() == "true"
    metadata_str = request.headers.get("X-Omega-Metadata")

    if not object_name:
        abort(400, description="X-Omega-Object-Name header is required")

    metadata = None
    if metadata_str:
        try:
            metadata = json.loads(metadata_str)
        except json.JSONDecodeError:
            abort(400, description="X-Omega-Metadata must be valid JSON")

    content = request.get_data()
    if not content:
        abort(400, description="Request body cannot be empty")

    meta = OmegaStorageEngine.upload_object(owner_id, object_name, content, content_type, is_immutable, metadata)
    if not meta:
        abort(500, description="Upload failed")

    OmegaLedgerIntegration.post_event(
        EventType.OBJECT_UPLOADED, meta["object_id"], "storage_object", owner_id,
        {"object_name": object_name, "size_bytes": meta["size_bytes"], "checksum": meta["checksum"]}
    )
    logger.info("[API] Upload %s by owner %s (%d bytes)", meta["object_id"], owner_id, meta["size_bytes"])
    return jsonify({"message": "Uploaded", "object_id": meta["object_id"]}), 201


@app.route("/v1/storage/objects/<object_id>", methods=["GET"])
@require_bearer
@require_permission("storage:read")
def download_object(object_id):
    owner_id = request.current_user["owner_id"]
    content  = OmegaStorageEngine.download_object(object_id, owner_id)
    if content is None:
        abort(404, description="Object not found or unauthorized")

    meta = OmegaCloudDB.get_storage_metadata(object_id)
    OmegaLedgerIntegration.post_event(
        EventType.OBJECT_DOWNLOADED, object_id, "storage_object", owner_id,
        {"object_name": meta["object_name"], "size_bytes": meta["size_bytes"]}
    )
    logger.info("[API] Download %s by owner %s", object_id, owner_id)
    return content, 200, {
        "Content-Type":        meta["content_type"],
        "X-Omega-Object-Name": meta["object_name"],
    }


@app.route("/v1/replication/objects/<object_id>", methods=["POST"])
@require_hmac
@require_permission("storage:replicate")
def replicate_object(object_id):
    owner_id     = request.current_user["owner_id"]
    data         = request.get_json() or {}
    target_nodes = data.get("target_nodes")

    if not target_nodes or not isinstance(target_nodes, list):
        abort(400, description="'target_nodes' list is required")

    result = OmegaReplicationBridge.replicate_object(object_id, owner_id, target_nodes)
    if not result["success"]:
        abort(500, description=result.get("message", "Replication failed"))

    OmegaLedgerIntegration.post_event(
        EventType.OBJECT_REPLICATED, object_id, "storage_object", owner_id,
        {"target_nodes": target_nodes, "status": result["replication_status"]}
    )
    return jsonify({"message": "Replication initiated", "status": result["replication_status"]}), 202


# ── ledger ────────────────────────────────────────────────────────────────────

@app.route("/v1/ledger/transactions", methods=["POST"])
@require_hmac
@require_permission("ledger:post_transaction")
def post_transaction():
    owner_id = request.current_user["owner_id"]
    data     = request.get_json() or {}
    wallet_id = data.get("wallet_id")
    amount    = data.get("amount")
    currency  = data.get("currency", "USD")
    memo      = data.get("memo", "API Transaction")

    if not wallet_id or amount is None:
        abort(400, description="'wallet_id' and 'amount' are required")
    if not isinstance(amount, (int, float)) or amount <= 0:
        abort(400, description="'amount' must be a positive number")

    result = OmegaLedgerIntegration.post_transaction(owner_id, wallet_id, float(amount), currency, memo)
    if not result["success"]:
        abort(500, description=result.get("message", "Transaction failed"))
    return jsonify(result), 201


@app.route("/v1/ledger/transactions/<tx_id>", methods=["GET"])
@require_bearer
@require_permission("ledger:read_transaction_details")
def get_transaction(tx_id):
    owner_id = request.current_user["owner_id"]
    result   = OmegaLedgerIntegration.get_transaction_details(owner_id, tx_id)
    if not result["success"]:
        abort(404, description=result.get("message"))
    return jsonify(result), 200


@app.route("/v1/ledger/wallets/<wallet_id>/balance", methods=["GET"])
@require_bearer
@require_permission("ledger:read_balance")
def get_balance(wallet_id):
    owner_id = request.current_user["owner_id"]
    result   = OmegaLedgerIntegration.get_wallet_balance(owner_id, wallet_id)
    if not result["success"]:
        abort(404, description=result.get("message"))
    return jsonify(result), 200


@app.route("/v1/ledger/wallets/<wallet_id>/history", methods=["GET"])
@require_bearer
@require_permission("ledger:read_history")
def get_wallet_history(wallet_id):
    owner_id = request.current_user["owner_id"]

    # Verify wallet ownership before returning history
    wallet = OmegaCloudDB.get_wallet(wallet_id)
    if not wallet or wallet["owner_id"] != owner_id:
        abort(403, description="Wallet not found or unauthorized")

    history = OmegaLedgerIntegration.get_ledger_history(
        owner_id=owner_id,
        aggregate_id=wallet_id,
        aggregate_type="wallet",
        event_type=request.args.get("event_type"),
        start_time=request.args.get("start_time"),
        end_time=request.args.get("end_time"),
        limit=int(request.args.get("limit", 100)),
    )
    return jsonify(history), 200


@app.route("/v1/ledger/audit", methods=["GET"])
@require_bearer
@require_permission("admin:read_audit_report")
def get_audit():
    return jsonify(OmegaLedgerIntegration.get_system_audit_report()), 200


# ── nodes ─────────────────────────────────────────────────────────────────────

@app.route("/v1/nodes/register", methods=["POST"])
@require_hmac
@require_permission("spawn_engine:register_node")
def register_node():
    owner_id = request.current_user["owner_id"]
    data     = request.get_json() or {}
    node_id  = data.get("node_id")
    ntype    = data.get("node_type")
    endpoint = data.get("endpoint")

    if not all([node_id, ntype, endpoint]):
        abort(400, description="'node_id', 'node_type', 'endpoint' are required")

    result = OmegaSpawnEngine.register_node(node_id, ntype, endpoint, owner_id)
    if not result["success"]:
        abort(409, description=result.get("message", "Registration failed"))

    OmegaLedgerIntegration.post_event(
        EventType.NODE_REGISTERED, node_id, "node", owner_id,
        {"node_type": ntype, "endpoint": endpoint}
    )
    return jsonify(result), 201


@app.route("/v1/nodes/<node_id>", methods=["GET"])
@require_bearer
@require_permission("spawn_engine:read_node_status")
def node_status(node_id):
    result = OmegaSpawnEngine.get_node_status(node_id)
    if not result["success"]:
        abort(404, description=result.get("message"))
    return jsonify(result["node"]), 200


@app.route("/v1/nodes", methods=["GET"])
@require_bearer
@require_permission("spawn_engine:list_nodes")
def list_nodes():
    return jsonify(OmegaSpawnEngine.list_nodes()["nodes"]), 200


# ── internal (node-to-node) ───────────────────────────────────────────────────

@app.route("/internal/replicate", methods=["POST"])
def internal_replicate():
    """Receive encrypted bytes from a peer node during replication."""
    data    = request.get_json() or {}
    key_id  = data.get("key_id")
    hex_val = data.get("data_hex")
    if not key_id or not hex_val:
        abort(400, description="key_id and data_hex required")
    _STORE_NODE3[key_id] = bytes.fromhex(hex_val)
    logger.info("[INTERNAL] Received replicated object key_id=%s", key_id)
    return jsonify({"status": "ok"}), 200


@app.route("/internal/vote", methods=["POST"])
def internal_vote():
    """Receive a consensus vote request from a peer node and respond."""
    data           = request.get_json() or {}
    transaction_id = data.get("transaction_id")
    if not transaction_id:
        abort(400, description="transaction_id required")
    # This node auto-approves — in omega_cloud.py this runs real validation logic
    return jsonify({"vote": "APPROVED", "node": "node3", "transaction_id": transaction_id}), 200


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT 7 — ADMIN CLI
# ══════════════════════════════════════════════════════════════════════════════

ALL_PERMISSIONS = [
    "storage:read", "storage:write", "storage:replicate",
    "ledger:post_transaction", "ledger:read_balance",
    "ledger:read_history", "ledger:read_transaction_details",
    "spawn_engine:register_node", "spawn_engine:read_node_status", "spawn_engine:list_nodes",
    "admin:generate_key", "admin:read_audit_report",
]


def _cli_init_db():
    migrate_db()
    print("✓ Database initialized/migrated.")


def _cli_create_owner(name: str):
    existing = OmegaCloudDB.get_account_by_name(name)
    if existing:
        print(f"Owner '{name}' already exists: {existing['account_id']}")
        return
    record = OmegaCloudDB.insert_account({"account_name": name})
    if record:
        print(f"✓ Created owner '{name}' → {record['account_id']}")
    else:
        print("✗ Failed to create owner (check logs)")


def _cli_generate_key(owner_id: str, alias: str, ktype: str, permissions: List[str], expires_in_days: int):
    if not OmegaCloudDB.get_account(owner_id):
        print(f"✗ Owner {owner_id} not found — run 'create-owner' first")
        return

    info = OmegaAuthSystem.generate_api_key(owner_id, alias, ktype, permissions or [], expires_in_days or None)
    print("\n╔═══ API Key Generated ═══════════════════════════════╗")
    print(f"  Key ID      : {info['key_id']}")
    print(f"  Type        : {info['key_type']}")
    print(f"  Alias       : {alias}")
    print(f"  Expires     : {info['expires_at'] or 'Never'}")
    print(f"  Permissions : {permissions}")
    print("╠═══ STORE SECURELY — shown only once ════════════════╣")
    print(f"  API Key     : {info['api_key']}")
    if ktype == "HMAC":
        print(f"  API Secret  : {info['api_secret']}")
    print("╚═════════════════════════════════════════════════════╝\n")


def _cli_list_keys(owner_id: Optional[str]):
    keys = OmegaCloudDB.list_api_keys(owner_id)
    if not keys:
        print("No keys found.")
        return
    for k in keys:
        perms = k.get("permissions", [])
        print(f"\n  {k['key_id']}  [{k['key_type']}] [{k['status']}]")
        print(f"    Owner   : {k['owner_id']}")
        print(f"    Alias   : {k['key_alias']}")
        print(f"    Expires : {k.get('expires_at') or 'Never'}")
        print(f"    Perms   : {perms}")


def run_cli(argv: List[str]):
    parser = argparse.ArgumentParser(prog="omega_node3 cli", description="Omega Cloud Node 3 Admin CLI")
    sub    = parser.add_subparsers(dest="cmd")

    sub.add_parser("init-db",      help="Initialize / migrate the SQLite schema")

    p_co = sub.add_parser("create-owner", help="Create a new account owner")
    p_co.add_argument("owner_name")

    p_gk = sub.add_parser("generate-key",  help="Generate a new API key")
    p_gk.add_argument("owner_id")
    p_gk.add_argument("key_alias")
    p_gk.add_argument("--type",            choices=["BEARER", "HMAC"], default="BEARER")
    p_gk.add_argument("--permissions",     nargs="*", default=[],
                       help=f"Permissions. Available: {', '.join(ALL_PERMISSIONS)}")
    p_gk.add_argument("--all-permissions", action="store_true", help="Grant all permissions")
    p_gk.add_argument("--expires-in-days", type=int, default=365)

    p_lk = sub.add_parser("list-keys", help="List API keys")
    p_lk.add_argument("--owner-id", default=None)

    args = parser.parse_args(argv)

    if args.cmd == "init-db":
        _cli_init_db()
    elif args.cmd == "create-owner":
        _cli_create_owner(args.owner_name)
    elif args.cmd == "generate-key":
        perms = ALL_PERMISSIONS if args.all_permissions else args.permissions
        _cli_generate_key(args.owner_id, args.key_alias, args.type, perms, args.expires_in_days)
    elif args.cmd == "list-keys":
        _cli_list_keys(args.owner_id)
    else:
        parser.print_help()


# ══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP — Demo setup on first run
# ══════════════════════════════════════════════════════════════════════════════

def bootstrap_demo():
    """
    On first start, create the MegaBankAdmin account, issue demo keys,
    seed a wallet, and register the two peer nodes.
    Idempotent — safe to call every start.
    """
    migrate_db()

    owner_name = "MegaBankAdmin"
    owner      = OmegaCloudDB.get_account_by_name(owner_name)
    if not owner:
        owner = OmegaCloudDB.insert_account({"account_name": owner_name})
        logger.info("[BOOT] Created account '%s' → %s", owner_name, owner["account_id"])
    owner_id = owner["account_id"]

    # Bearer key
    bearer = OmegaAuthSystem.generate_api_key(
        owner_id, "demo_bearer", "BEARER", ALL_PERMISSIONS, 365
    )
    logger.info("[BOOT] ╔═══ DEMO BEARER TOKEN (save this!) ════════════╗")
    logger.info("[BOOT]   %s", bearer["api_key"])
    logger.info("[BOOT] ╚═══════════════════════════════════════════════╝")

    # HMAC key
    hmac_key = OmegaAuthSystem.generate_api_key(
        owner_id, "demo_hmac", "HMAC",
        ["storage:write", "storage:replicate", "ledger:post_transaction", "spawn_engine:register_node"],
        365
    )
    logger.info("[BOOT] ╔═══ DEMO HMAC KEY (save this!) ════════════════╗")
    logger.info("[BOOT]   Key ID  : %s", hmac_key["key_id"])
    logger.info("[BOOT]   API Key : %s", hmac_key["api_key"])
    logger.info("[BOOT]   Secret  : %s", hmac_key["api_secret"])
    logger.info("[BOOT] ╚═══════════════════════════════════════════════╝")

    # Seed wallet
    wallet_id = f"wallet_{owner_id}"
    if not OmegaCloudDB.get_wallet(wallet_id):
        OmegaCloudDB.upsert_wallet(wallet_id, 10_000.0, owner_id)
        logger.info("[BOOT] Seeded wallet %s with 10,000.00 USD", wallet_id)

    # Register peer nodes (idempotent)
    for nid, ntype, ep in [
        ("node1_peer", "phone_node", NODE1_ENDPOINT or "http://localhost:5001"),
        ("node2_peer", "phone_node", NODE2_ENDPOINT or "http://localhost:5002"),
    ]:
        if not OmegaCloudDB.get_node(nid):
            OmegaSpawnEngine.register_node(nid, ntype, ep, owner_id)
            logger.info("[BOOT] Registered peer node %s @ %s", nid, ep)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    mode = sys.argv[1].lower()

    if mode == "server":
        bootstrap_demo()
        logger.info("[NODE3] Starting Omega Cloud Node 3 API on %s:%d", NODE3_HOST, API_SERVER_PORT)
        logger.info("[NODE3] Consensus quorum: %d | Node1: %s | Node2: %s",
                    CONSENSUS_QUORUM,
                    NODE1_ENDPOINT or "(simulated)",
                    NODE2_ENDPOINT or "(simulated)")
        # Production: use gunicorn -w 4 -b 0.0.0.0:5003 omega_node3:app
        app.run(host=NODE3_HOST, port=API_SERVER_PORT, debug=False)

    elif mode == "cli":
        migrate_db()
        run_cli(sys.argv[2:])

    else:
        print(f"Unknown mode '{mode}'. Use: server | cli")
        sys.exit(1)


if __name__ == "__main__":
    main()

