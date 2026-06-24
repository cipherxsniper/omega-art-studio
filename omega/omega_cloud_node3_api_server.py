import sqlite3

import os
import json
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import uuid
from functools import wraps
from enum import Enum
import logging

from flask import Flask, request, jsonify, abort
from werkzeug.exceptions import HTTPException

# Import database functions
from database import get_db_connection, migrate_db, DATABASE_FILE

# --- Configuration ---
MASTER_ENCRYPTION_KEY = hashlib.sha256(os.getenv("MASTER_ENCRYPTION_KEY", "super_secret_master_key_for_omega_cloud").encode()).digest()
API_SERVER_PORT = int(os.getenv("API_SERVER_PORT", 5000))

# Minimum number of ledger nodes that must acknowledge a transaction
# before it is considered final (simulated consensus quorum).
CONSENSUS_QUORUM = int(os.getenv("CONSENSUS_QUORUM", 2))

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- Simulated storage for encrypted content (in-memory for now, will be replaced by file storage later) ---
_SIMULATED_ENCRYPTED_STORAGE: Dict[str, bytes] = {}
_SIMULATED_NODE1_STORAGE: Dict[str, bytes] = {}
_SIMULATED_NODE2_STORAGE: Dict[str, bytes] = {}

# --- Enums ---
class EventType(str, Enum):
    TRANSACTION_INITIATED  = "TRANSACTION_INITIATED"
    TRANSACTION_VALIDATED  = "TRANSACTION_VALIDATED"
    TRANSACTION_COMMITTED  = "TRANSACTION_COMMITTED"
    TRANSACTION_REJECTED   = "TRANSACTION_REJECTED"
    WALLET_CREDITED        = "WALLET_CREDITED"
    WALLET_DEBITED         = "WALLET_DEBITED"
    CONSENSUS_VOTE_CAST    = "CONSENSUS_VOTE_CAST"
    CONSENSUS_REACHED      = "CONSENSUS_REACHED"
    OBJECT_UPLOADED        = "OBJECT_UPLOADED"
    OBJECT_DOWNLOADED      = "OBJECT_DOWNLOADED"
    OBJECT_REPLICATED      = "OBJECT_REPLICATED"
    NODE_REGISTERED        = "NODE_REGISTERED"

class TransactionStatus(str, Enum):
    PENDING   = "PENDING"
    VALIDATED = "VALIDATED"
    FINAL     = "FINAL"
    REJECTED  = "REJECTED"


# ---------------------------------------------------------------------------
# OmegaCloudDB
# ---------------------------------------------------------------------------
class OmegaCloudDB:
    """Database interactions for Omega Cloud Node 3 using SQLite."""

    @staticmethod
    def _execute_query(table_name: str, query_type: str, data: Dict[str, Any], pk_field: str = "id", fetch_one=False, fetch_all=False) -> Optional[Dict[str, Any]] or List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        result = None

        try:
            if query_type == "INSERT":
                new_id = data.get(pk_field, str(uuid.uuid4()))
                data[pk_field] = new_id
                data["created_at"] = datetime.now(timezone.utc).isoformat()
                if "updated_at" not in data:
                    data["updated_at"] = datetime.now(timezone.utc).isoformat()

                columns = ", ".join(data.keys())
                placeholders = ", ".join(["?" for _ in data.values()])
                values = []
                for k, v in data.items():
                    if isinstance(v, (dict, list)):
                        values.append(json.dumps(v))
                    elif isinstance(v, bool):
                        values.append(1 if v else 0)
                    else:
                        values.append(v)

                cursor.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", tuple(values))
                conn.commit()
                result = data

            elif query_type == "SELECT":
                conditions = []
                values = []
                for k, v in data.items():
                    conditions.append(f"{k} = ?")
                    if isinstance(v, (dict, list)):
                        values.append(json.dumps(v))
                    elif isinstance(v, bool):
                        values.append(1 if v else 0)
                    else:
                        values.append(v)
                
                query = f"SELECT * FROM {table_name}"
                if conditions:
                    query += f" WHERE {" AND ".join(conditions)}"
                
                cursor.execute(query, tuple(values))
                if fetch_one:
                    row = cursor.fetchone()
                    if row:
                        result = dict(row)
                        # Deserialize JSON fields and convert boolean integers
                        for k, v in result.items():
                            if k in ["storage_location", "permissions", "metadata", "event_data"] and isinstance(v, str):
                                try:
                                    result[k] = json.loads(v)
                                except json.JSONDecodeError:
                                    pass # Keep as string if not valid JSON
                            if k in ["is_immutable"] and isinstance(v, int):
                                result[k] = bool(v)
                elif fetch_all:
                    rows = cursor.fetchall()
                    result = []
                    for row in rows:
                        record = dict(row)
                        for k, v in record.items():
                            if k in ["storage_location", "permissions", "metadata", "event_data"] and isinstance(v, str):
                                try:
                                    record[k] = json.loads(v)
                                except json.JSONDecodeError:
                                    pass
                            if k in ["is_immutable"] and isinstance(v, int):
                                record[k] = bool(v)
                        result.append(record)

            elif query_type == "UPDATE":
                record_id = data.pop(pk_field)
                data["updated_at"] = datetime.now(timezone.utc).isoformat()

                set_clauses = []
                values = []
                for k, v in data.items():
                    set_clauses.append(f"{k} = ?")
                    if isinstance(v, (dict, list)):
                        values.append(json.dumps(v))
                    elif isinstance(v, bool):
                        values.append(1 if v else 0)
                    else:
                        values.append(v)
                values.append(record_id)

                cursor.execute(f"UPDATE {table_name} SET {", ".join(set_clauses)} WHERE {pk_field} = ?", tuple(values))
                conn.commit()
                result = OmegaCloudDB._execute_query(table_name, "SELECT", {pk_field: record_id}, pk_field, fetch_one=True)

            elif query_type == "DELETE":
                record_id = data.pop(pk_field)
                cursor.execute(f"DELETE FROM {table_name} WHERE {pk_field} = ?", (record_id,))
                conn.commit()
                result = {"status": "deleted"}

        except sqlite3.Error as e:
            logger.error(f"Database error during {query_type} on {table_name}: {e}")
            conn.rollback()
        finally:
            conn.close()
        return result

    @staticmethod
    def insert_account(data: Dict[str, Any]) -> Dict[str, Any]:
        return OmegaCloudDB._execute_query("omega_accounts", "INSERT", data, "account_id")

    @staticmethod
    def get_account(account_id: str) -> Optional[Dict[str, Any]]:
        return OmegaCloudDB._execute_query("omega_accounts", "SELECT", {"account_id": account_id}, "account_id", fetch_one=True)

    @staticmethod
    def get_account_by_name(account_name: str) -> Optional[Dict[str, Any]]:
        return OmegaCloudDB._execute_query("omega_accounts", "SELECT", {"account_name": account_name}, "account_id", fetch_one=True)

    @staticmethod
    def insert_storage_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
        return OmegaCloudDB._execute_query("omega_storage_metadata", "INSERT", data, "object_id")

    @staticmethod
    def get_storage_metadata(object_id: str) -> Optional[Dict[str, Any]]:
        return OmegaCloudDB._execute_query("omega_storage_metadata", "SELECT", {"object_id": object_id}, "object_id", fetch_one=True)

    @staticmethod
    def update_storage_metadata(object_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return OmegaCloudDB._execute_query("omega_storage_metadata", "UPDATE", data, "object_id")

    @staticmethod
    def insert_api_key(data: Dict[str, Any]) -> Dict[str, Any]:
        return OmegaCloudDB._execute_query("omega_api_keys", "INSERT", data, "key_id")

    @staticmethod
    def get_api_key(key_id: str) -> Optional[Dict[str, Any]]:
        return OmegaCloudDB._execute_query("omega_api_keys", "SELECT", {"key_id": key_id}, "key_id", fetch_one=True)

    @staticmethod
    def get_api_key_by_hash(api_key_hash: str) -> Optional[Dict[str, Any]]:
        return OmegaCloudDB._execute_query("omega_api_keys", "SELECT", {"api_key_hash": api_key_hash}, "key_id", fetch_one=True)

    @staticmethod
    def update_api_key(key_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = dict(data)
        data["key_id"] = key_id
        return OmegaCloudDB._execute_query("omega_api_keys", "UPDATE", data, "key_id")

    @staticmethod
    def insert_encryption_key(data: Dict[str, Any]) -> Dict[str, Any]:
        return OmegaCloudDB._execute_query("omega_encryption_keys", "INSERT", data, "key_id")

    @staticmethod
    def get_encryption_key(key_id: str) -> Optional[Dict[str, Any]]:
        return OmegaCloudDB._execute_query("omega_encryption_keys", "SELECT", {"key_id": key_id}, "key_id", fetch_one=True)

    @staticmethod
    def insert_ledger_event(data: Dict[str, Any]) -> Dict[str, Any]:
        return OmegaCloudDB._execute_query("omega_ledger_events", "INSERT", data, "event_id")

    @staticmethod
    def get_latest_event_hash(aggregate_id: str) -> Optional[str]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT event_hash FROM omega_ledger_events WHERE aggregate_id = ? ORDER BY timestamp DESC LIMIT 1",
            (aggregate_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return row["event_hash"] if row else None

    @staticmethod
    def get_ledger_events(filter_conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        return OmegaCloudDB._execute_query("omega_ledger_events", "SELECT", filter_conditions, fetch_all=True) or []

    @staticmethod
    def insert_consensus_vote(data: Dict[str, Any]) -> Dict[str, Any]:
        return OmegaCloudDB._execute_query("omega_consensus_votes", "INSERT", data, "vote_id")

    @staticmethod
    def get_consensus_votes(transaction_id: str) -> List[Dict[str, Any]]:
        return OmegaCloudDB._execute_query("omega_consensus_votes", "SELECT", {"transaction_id": transaction_id}, fetch_all=True) or []

    @staticmethod
    def get_wallet(wallet_id: str) -> Optional[Dict[str, Any]]:
        return OmegaCloudDB._execute_query("omega_wallets", "SELECT", {"wallet_id": wallet_id}, "wallet_id", fetch_one=True)

    @staticmethod
    def get_wallet_balance_db(wallet_id: str) -> float:
        wallet = OmegaCloudDB.get_wallet(wallet_id)
        return wallet.get("balance", 0.0) if wallet else 0.0

    @staticmethod
    def update_wallet_balance_db(wallet_id: str, amount: float, owner_id: str):
        wallet = OmegaCloudDB.get_wallet(wallet_id)
        if wallet:
            new_balance = wallet["balance"] + amount
            OmegaCloudDB._execute_query("omega_wallets", "UPDATE", {"wallet_id": wallet_id, "balance": new_balance}, "wallet_id")
        else:
            OmegaCloudDB._execute_query("omega_wallets", "INSERT", {"wallet_id": wallet_id, "balance": amount, "owner_id": owner_id, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}, "wallet_id")

    @staticmethod
    def insert_node(data: Dict[str, Any]) -> Dict[str, Any]:
        return OmegaCloudDB._execute_query("omega_nodes", "INSERT", data, "node_id")

    @staticmethod
    def get_node(node_id: str) -> Optional[Dict[str, Any]]:
        return OmegaCloudDB._execute_query("omega_nodes", "SELECT", {"node_id": node_id}, "node_id", fetch_one=True)

    @staticmethod
    def get_all_nodes() -> List[Dict[str, Any]]:
        return OmegaCloudDB._execute_query("omega_nodes", "SELECT", {}, fetch_all=True) or []


# --- Component 1: Storage Engine Implementation ---
class OmegaStorageEngine:
    """Handles encrypted object storage and metadata management."""

    @staticmethod
    def _derive_encryption_key(key_id: uuid.UUID, master_key: bytes) -> bytes:
        """Derives a unique encryption key for an object from the master key and object's key_id."""
        return hmac.new(master_key, str(key_id).encode(), hashlib.sha256).digest()

    @staticmethod
    def _xor_crypt(data: bytes, key: bytes) -> bytes:
        """Simple XOR encryption/decryption for demonstration purposes."""
        return bytes(d ^ k for d, k in zip(data, key * (len(data) // len(key) + 1)))

    @staticmethod
    def encrypt_data(data: bytes, encryption_key_id: uuid.UUID) -> bytes:
        """Encrypts data using a derived key."""
        derived_key = OmegaStorageEngine._derive_encryption_key(encryption_key_id, MASTER_ENCRYPTION_KEY)
        return OmegaStorageEngine._xor_crypt(data, derived_key)

    @staticmethod
    def decrypt_data(encrypted_data: bytes, encryption_key_id: uuid.UUID) -> bytes:
        """Decrypts data using a derived key."""
        derived_key = OmegaStorageEngine._derive_encryption_key(encryption_key_id, MASTER_ENCRYPTION_KEY)
        return OmegaStorageEngine._xor_crypt(encrypted_data, derived_key)

    @staticmethod
    def upload_object(
        owner_id: str,
        object_name: str,
        content: bytes,
        content_type: str,
        is_immutable: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Uploads an object, encrypts it, and stores its metadata."""
        encryption_key_id = uuid.uuid4()
        OmegaCloudDB.insert_encryption_key({
            "key_id": str(encryption_key_id),
            "owner_id": owner_id,
            "key_material_encrypted": "<derived_from_master_key>", # Master key derives it
            "key_type": "AES256",
            "status": "ACTIVE"
        })

        encrypted_content = OmegaStorageEngine.encrypt_data(content, encryption_key_id)
        checksum = hashlib.sha256(encrypted_content).hexdigest()

        # Store encrypted content in Node 3's simulated storage
        _SIMULATED_ENCRYPTED_STORAGE[str(encryption_key_id)] = encrypted_content

        storage_metadata = {
            "owner_id": owner_id,
            "object_name": object_name,
            "content_type": content_type,
            "size_bytes": len(content),
            "checksum": checksum,
            "encryption_key_id": str(encryption_key_id),
            "storage_location": {"node3": True, "node1_replicated": False, "node2_replicated": False}, # Initial state
            "is_immutable": is_immutable,
            "metadata": metadata or {}
        }
        return OmegaCloudDB.insert_storage_metadata(storage_metadata)

    @staticmethod
    def download_object(object_id: str, owner_id: str) -> Optional[bytes]:
        """Retrieves and decrypts an object."""
        metadata = OmegaCloudDB.get_storage_metadata(object_id)

        if not metadata or metadata["owner_id"] != owner_id:
            logger.warning(f"[SECURITY] Unauthorized attempt to download object {object_id} by owner {owner_id}")
            return None

        encryption_key_id = uuid.UUID(metadata["encryption_key_id"])
        checksum = metadata["checksum"]

        # Try to retrieve from Node 3 storage first
        encrypted_content = _SIMULATED_ENCRYPTED_STORAGE.get(str(encryption_key_id))

        # If not found in Node 3, try replicated nodes (simulated)
        if not encrypted_content:
            if metadata.get("storage_location", {}).get("node1_replicated"):
                encrypted_content = _SIMULATED_NODE1_STORAGE.get(str(encryption_key_id))
                logger.info(f"[STORAGE] Retrieved from simulated Node 1 storage for {object_id}")
            elif metadata.get("storage_location", {}).get("node2_replicated"):
                encrypted_content = _SIMULATED_NODE2_STORAGE.get(str(encryption_key_id))
                logger.info(f"[STORAGE] Retrieved from simulated Node 2 storage for {object_id}")

        if not encrypted_content:
            logger.warning(f"[STORAGE] Encrypted content not found in any simulated storage for {object_id}")
            return None

        if hashlib.sha256(encrypted_content).hexdigest() != checksum:
            logger.error(f"[STORAGE] Checksum mismatch for object {object_id}. Data corruption or tampering detected.")
            return None

        decrypted_content = OmegaStorageEngine.decrypt_data(encrypted_content, encryption_key_id)
        return decrypted_content


# --- Component 2: API Keys and Authentication System Implementation ---
class OmegaAuthSystem:
    """Manages API key generation, validation, and HMAC signature verification."""

    @staticmethod
    def _hash_key(key: str) -> str:
        """Hashes an API key or secret for storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def generate_api_key(
        owner_id: str,
        key_alias: str,
        key_type: str = "BEARER",
        permissions: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None
    ) -> Dict[str, str]:
        """Generates a new API key (Bearer or HMAC)."""
        raw_api_key = secrets.token_urlsafe(32) # The actual key given to the user
        api_key_hash = OmegaAuthSystem._hash_key(raw_api_key)
        raw_api_secret = None
        api_secret_hash = None

        if key_type == "HMAC":
            raw_api_secret = secrets.token_urlsafe(64)
            api_secret_hash = raw_api_secret # Store raw secret for HMAC demo (DANGER in prod)

        expires_at = None
        if expires_in_days:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_in_days)).isoformat()

        key_data = {
            "owner_id": owner_id,
            "key_alias": key_alias,
            "api_key_hash": api_key_hash,
            "api_secret_hash": api_secret_hash,
            "key_type": key_type,
            "permissions": permissions or [],
            "status": "ACTIVE",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at,
            "last_used_at": None
        }
        db_record = OmegaCloudDB.insert_api_key(key_data)

        return {
            "key_id": db_record["key_id"],
            "api_key": raw_api_key,
            "api_secret": raw_api_secret if key_type == "HMAC" else "",
            "key_type": key_type,
            "expires_at": expires_at
        }

    @staticmethod
    def validate_bearer_token(token: str) -> Optional[Dict[str, Any]]:
        """Validates a bearer token and returns key details if valid."""
        api_key_hash = OmegaAuthSystem._hash_key(token)
        key_data = OmegaCloudDB.get_api_key_by_hash(api_key_hash)

        if not key_data or key_data["key_type"] != "BEARER" or key_data["status"] != "ACTIVE":
            logger.warning(f"[AUTH] Invalid or inactive Bearer token attempt.")
            return None

        if key_data["expires_at"] and datetime.fromisoformat(key_data["expires_at"]) < datetime.now(timezone.utc):
            OmegaCloudDB.update_api_key(key_data["key_id"], {"status": "EXPIRED"})
            logger.warning(f"[AUTH] Expired Bearer token used: {key_data["key_id"]}.")
            return None

        OmegaCloudDB.update_api_key(key_data["key_id"], {"last_used_at": datetime.now(timezone.utc).isoformat()})
        return key_data

    @staticmethod
    def verify_hmac_signature(
        api_key_id: str,
        timestamp: str,
        nonce: str,
        request_method: str,
        request_path: str,
        request_body: bytes,
        signature: str
    ) -> Optional[Dict[str, Any]]:
        """Verifies an HMAC signature for a request."""
        key_data = OmegaCloudDB.get_api_key(api_key_id)

        if not key_data or key_data["key_type"] != "HMAC" or key_data["status"] != "ACTIVE":
            logger.warning(f"[AUTH] HMAC key {api_key_id} not found or inactive.")
            return None

        if key_data["expires_at"] and datetime.fromisoformat(key_data["expires_at"]) < datetime.now(timezone.utc):
            OmegaCloudDB.update_api_key(key_data["key_id"], {"status": "EXPIRED"})
            logger.warning(f"[AUTH] HMAC key {api_key_id} expired.")
            return None

        raw_api_secret = key_data["api_secret_hash"] # For demo, this is the raw secret

        string_to_sign = f"{request_method.upper()}\n{request_path}\n{timestamp}\n{nonce}\n{hashlib.sha256(request_body).hexdigest()}"
        expected_signature = hmac.new(
            raw_api_secret.encode(),
            string_to_sign.encode(),
            hashlib.sha256
        ).hexdigest()

        if not secrets.compare_digest(expected_signature, signature):
            logger.warning(f"[AUTH] HMAC signature mismatch for key {api_key_id}. Expected {expected_signature}, got {signature}")
            return None

        current_time = datetime.now(timezone.utc)
        request_time = datetime.fromisoformat(timestamp)
        if abs((current_time - request_time).total_seconds()) > 300: # 5 minute window
            logger.warning(f"[AUTH] Timestamp too old or too far in future for key {api_key_id}.")
            return None

        OmegaCloudDB.update_api_key(key_data["key_id"], {"last_used_at": datetime.now(timezone.utc).isoformat()})
        return key_data


# --- Component 3: Cloud API Server ---
app = Flask(__name__)

# --- Global Error Handler ---
@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    response = e.get_response()
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response

# --- Authentication Decorators ---
def require_bearer_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            abort(401, description="Authorization header missing or malformed")
        
        token = auth_header.split(" ")[1]
        key_data = OmegaAuthSystem.validate_bearer_token(token)
        
        if not key_data:
            abort(401, description="Invalid or expired Bearer token")
        
        request.current_user = key_data # Attach user info to request context
        return f(*args, **kwargs)
    return decorated

def require_hmac_signature(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key_id = request.headers.get("X-Omega-Api-Key-Id")
        timestamp = request.headers.get("X-Omega-Timestamp")
        nonce = request.headers.get("X-Omega-Nonce")
        signature = request.headers.get("X-Omega-Signature")

        if not all([api_key_id, timestamp, nonce, signature]):
            abort(401, description="Missing HMAC authentication headers")

        request_body = request.get_data()

        key_data = OmegaAuthSystem.verify_hmac_signature(
            api_key_id=api_key_id,
            timestamp=timestamp,
            nonce=nonce,
            request_method=request.method,
            request_path=request.path,
            request_body=request_body,
            signature=signature
        )

        if not key_data:
            abort(401, description="Invalid HMAC signature or credentials")
        
        request.current_user = key_data
        return f(*args, **kwargs)
    return decorated

def check_permission(permission: str):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user') or permission not in request.current_user.get('permissions', []):
                abort(403, description=f"Insufficient permissions: {permission} required")
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# --- Replication Bridge Placeholder ---
class OmegaReplicationBridge:
    """Simulates replication to other Omega nodes (e.g., phone storage)."""

    @staticmethod
    def replicate_object(object_id: str, owner_id: str, target_nodes: List[str]) -> Dict[str, Any]:
        """Simulates replicating an object to specified target nodes."""
        metadata = OmegaCloudDB.get_storage_metadata(object_id)
        if not metadata or metadata["owner_id"] != owner_id:
            logger.warning(f"[SECURITY] Unauthorized replication attempt for object {object_id} by owner {owner_id}")
            return {"success": False, "message": "Object not found or unauthorized"}

        encryption_key_id = metadata["encryption_key_id"]
        encrypted_content = _SIMULATED_ENCRYPTED_STORAGE.get(encryption_key_id)

        if not encrypted_content:
            logger.error(f"[REPLICATION] Encrypted content not found in Node 3 storage for {object_id}")
            return {"success": False, "message": "Encrypted content not found in Node 3 storage"}

        replication_status = {}
        updated_storage_locations = metadata.get("storage_location", {})

        for node in target_nodes:
            if node == "node1":
                _SIMULATED_NODE1_STORAGE[encryption_key_id] = encrypted_content
                updated_storage_locations["node1_replicated"] = True
                replication_status["node1_replicated"] = True
                logger.info(f"[REPLICATION] Replicated object {object_id} to simulated Node 1")
            elif node == "node2":
                _SIMULATED_NODE2_STORAGE[encryption_key_id] = encrypted_content
                updated_storage_locations["node2_replicated"] = True
                replication_status["node2_replicated"] = True
                logger.info(f"[REPLICATION] Replicated object {object_id} to simulated Node 2")
            else:
                replication_status[node] = False # Unknown or unsupported node
                logger.warning(f"[REPLICATION] Failed to replicate to unknown node: {node}")
        
        OmegaCloudDB.update_storage_metadata(object_id, {"storage_location": updated_storage_locations})
        return {"success": True, "replication_status": replication_status}


# --- Component 4: Ledger Integration Service (Re-engineered) ---
class OmegaLedgerIntegration:
    """Handles event sourcing, consensus, and querying for the Omega Ledger."""

    @staticmethod
    def _calculate_event_hash(event_data: Dict[str, Any], previous_event_hash: Optional[str]) -> str:
        """Calculates a cryptographic hash for an event, chaining it to the previous event."""
        event_string = json.dumps(event_data, sort_keys=True)
        combined_string = f"{event_string}-{previous_event_hash or ''}"
        return hashlib.sha256(combined_string.encode()).hexdigest()

    @staticmethod
    def post_event(
        event_type: EventType,
        aggregate_id: str,
        aggregate_type: str,
        owner_id: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Posts a new event to the ledger, ensuring event sourcing principles."""
        previous_event_hash = OmegaCloudDB.get_latest_event_hash(aggregate_id)
        event_hash = OmegaLedgerIntegration._calculate_event_hash(event_data, previous_event_hash)

        event_record = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type.value,
            "aggregate_id": aggregate_id,
            "aggregate_type": aggregate_type,
            "owner_id": owner_id,
            "event_data": event_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_event_hash": previous_event_hash,
            "event_hash": event_hash
        }
        inserted_event = OmegaCloudDB.insert_ledger_event(event_record)
        if not inserted_event:
            logger.error(f"[LEDGER] Failed to insert event {event_type} for aggregate {aggregate_id}")
        return inserted_event

    @staticmethod
    def get_transaction_status(transaction_id: str) -> Dict[str, Any]:
        """Determines the current status of a transaction based on its events and consensus votes."""
        events = OmegaCloudDB.get_ledger_events({"aggregate_id": transaction_id, "aggregate_type": "transaction"})
        
        status = TransactionStatus.PENDING
        votes = OmegaCloudDB.get_consensus_votes(transaction_id)
        approved_votes_count = sum(1 for v in votes if v["vote_status"] == "APPROVED")

        if any(e["event_type"] == EventType.TRANSACTION_REJECTED.value for e in events):
            status = TransactionStatus.REJECTED
        elif any(e["event_type"] == EventType.TRANSACTION_COMMITTED.value for e in events):
            status = TransactionStatus.FINAL
        elif any(e["event_type"] == EventType.TRANSACTION_VALIDATED.value for e in events):
            status = TransactionStatus.VALIDATED

        return {"transaction_id": transaction_id, "status": status.value, "event_count": len(events), "approved_votes": approved_votes_count, "required_quorum": CONSENSUS_QUORUM}

    @staticmethod
    def post_transaction(owner_id: str, wallet_id: str, amount: float, currency: str, memo: str) -> Dict[str, Any]:
        """Posts a transaction, which generates ledger events and initiates consensus."""
        if amount <= 0:
            logger.warning(f"[LEDGER] Attempted transaction with non-positive amount: {amount}")
            return {"success": False, "message": "Amount must be positive"}

        transaction_id = str(uuid.uuid4())
        event_data = {"transaction_id": transaction_id, "wallet_id": wallet_id, "amount": amount, "currency": currency, "memo": memo}
        
        # 1. Post a 'TransactionInitiated' event
        event_record = OmegaLedgerIntegration.post_event(
            event_type=EventType.TRANSACTION_INITIATED,
            aggregate_id=transaction_id,
            aggregate_type="transaction",
            owner_id=owner_id,
            event_data=event_data
        )
        if not event_record: return {"success": False, "message": "Failed to record transaction initiation event"}

        # 2. Simulate Node 3 voting for the transaction
        OmegaConsensusEngine.cast_vote(transaction_id, "node3_self", "APPROVED")
        OmegaLedgerIntegration.post_event(
            event_type=EventType.CONSENSUS_VOTE_CAST,
            aggregate_id=transaction_id,
            aggregate_type="transaction",
            owner_id=owner_id,
            event_data={"node_id": "node3_self", "vote": "APPROVED"}
        )

        # 3. Check for consensus (simplified: auto-approve if quorum met by simulated votes)
        current_status = OmegaLedgerIntegration.get_transaction_status(transaction_id)
        if current_status["approved_votes"] >= CONSENSUS_QUORUM:
            OmegaLedgerIntegration.post_event(
                event_type=EventType.TRANSACTION_VALIDATED,
                aggregate_id=transaction_id,
                aggregate_type="transaction",
                owner_id=owner_id,
                event_data={"status": "validated"}
            )
            # Apply the transaction (double-entry accounting)
            system_treasury_wallet_id = "system_treasury_wallet"
            OmegaCloudDB.update_wallet_balance_db(system_treasury_wallet_id, -amount, "system")
            OmegaCloudDB.update_wallet_balance_db(wallet_id, amount, owner_id)

            OmegaLedgerIntegration.post_event(
                event_type=EventType.WALLET_DEBITED,
                aggregate_id=system_treasury_wallet_id,
                aggregate_type="wallet",
                owner_id="system",
                event_data={"transaction_id": transaction_id, "amount": -amount}
            )
            OmegaLedgerIntegration.post_event(
                event_type=EventType.WALLET_CREDITED,
                aggregate_id=wallet_id,
                aggregate_type="wallet",
                owner_id=owner_id,
                event_data={"transaction_id": transaction_id, "amount": amount}
            )

            OmegaLedgerIntegration.post_event(
                event_type=EventType.TRANSACTION_COMMITTED,
                aggregate_id=transaction_id,
                aggregate_type="transaction",
                owner_id=owner_id,
                event_data={"status": "committed"}
            )
            logger.info(f"[LEDGER] Transaction {transaction_id} committed and wallet {wallet_id} updated.")
            return {"success": True, "transaction_id": transaction_id, "status": TransactionStatus.FINAL.value, "message": "Transaction posted and confirmed by ledger"}
        else:
            logger.info(f"[LEDGER] Transaction {transaction_id} initiated, awaiting further consensus.")
            return {"success": True, "transaction_id": transaction_id, "status": TransactionStatus.PENDING.value, "message": "Transaction initiated, awaiting consensus"}

    @staticmethod
    def get_wallet_balance(owner_id: str, wallet_id: str) -> Dict[str, Any]:
        """Retrieves the balance for a given wallet by querying the current state."""
        wallet = OmegaCloudDB.get_wallet(wallet_id)
        if not wallet or wallet["owner_id"] != owner_id: # Ensure owner has access
            logger.warning(f"[SECURITY] Unauthorized attempt to read wallet {wallet_id} by owner {owner_id}")
            return {"success": False, "message": "Wallet not found or unauthorized"}

        return {"success": True, "wallet_id": wallet_id, "balance": wallet["balance"], "currency": wallet["currency"]}

    @staticmethod
    def get_ledger_history(owner_id: str, aggregate_id: Optional[str] = None, aggregate_type: Optional[str] = None, 
                           event_type: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None, 
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves a history of events from the ledger, with filtering and pagination."""
        conditions = {"owner_id": owner_id}
        if aggregate_id: conditions["aggregate_id"] = aggregate_id
        if aggregate_type: conditions["aggregate_type"] = aggregate_type
        if event_type: conditions["event_type"] = event_type

        events = OmegaCloudDB.get_ledger_events(conditions)

        # Apply time filtering and limit in memory for simplicity (SQLite can do this more efficiently)
        filtered_events = []
        for event in events:
            event_time = datetime.fromisoformat(event["timestamp"])
            if start_time and event_time < datetime.fromisoformat(start_time): continue
            if end_time and event_time > datetime.fromisoformat(end_time): continue
            filtered_events.append(event)
        
        return sorted(filtered_events, key=lambda x: x["timestamp"], reverse=True)[:limit]

    @staticmethod
    def get_transaction_details(owner_id: str, transaction_id: str) -> Dict[str, Any]:
        """Retrieves full details for a transaction, including events and consensus votes."""
        tx_events = OmegaCloudDB.get_ledger_events({"aggregate_id": transaction_id, "aggregate_type": "transaction", "owner_id": owner_id})
        if not tx_events: return {"success": False, "message": "Transaction not found or unauthorized"}

        votes = OmegaCloudDB.get_consensus_votes(transaction_id)
        status_info = OmegaLedgerIntegration.get_transaction_status(transaction_id)

        return {
            "success": True,
            "transaction_id": transaction_id,
            "status": status_info["status"],
            "events": tx_events,
            "consensus_votes": votes,
            "approved_votes_count": status_info["approved_votes"],
            "required_quorum": status_info["required_quorum"]
        }

    @staticmethod
    def get_system_audit_report() -> Dict[str, Any]:
        """Generates a system-wide audit report for ledger activities."""
        all_transactions = OmegaCloudDB.get_ledger_events({"event_type": EventType.TRANSACTION_INITIATED.value})
        
        total_transactions = len(all_transactions)
        pending_transactions = 0
        final_transactions = 0
        rejected_transactions = 0

        for tx_event in all_transactions:
            tx_id = tx_event["aggregate_id"]
            status_info = OmegaLedgerIntegration.get_transaction_status(tx_id)
            if status_info["status"] == TransactionStatus.PENDING.value:
                pending_transactions += 1
            elif status_info["status"] == TransactionStatus.FINAL.value:
                final_transactions += 1
            elif status_info["status"] == TransactionStatus.REJECTED.value:
                rejected_transactions += 1
        
        return {
            "success": True,
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_transactions": total_transactions,
            "pending_transactions": pending_transactions,
            "final_transactions": final_transactions,
            "rejected_transactions": rejected_transactions,
            "consensus_quorum_setting": CONSENSUS_QUORUM
        }


# --- Component 4.1: Consensus Engine ---
class OmegaConsensusEngine:
    """Manages the BFT-lite consensus mechanism for transaction finality."""

    @staticmethod
    def cast_vote(transaction_id: str, node_id: str, vote_status: str) -> Dict[str, Any]:
        """Casts a vote for a given transaction by a node."""
        vote_record = {
            "vote_id": str(uuid.uuid4()),
            "transaction_id": transaction_id,
            "node_id": node_id,
            "vote_status": vote_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return OmegaCloudDB.insert_consensus_vote(vote_record)

    @staticmethod
    def get_transaction_votes(transaction_id: str) -> List[Dict[str, Any]]:
        """Retrieves all votes for a specific transaction."""
        return OmegaCloudDB.get_consensus_votes(transaction_id)


# --- Component 5: Spawn Engine Registration ---
class OmegaSpawnEngine:
    """Manages registration and status of Omega nodes."""

    @staticmethod
    def register_node(node_id: str, node_type: str, endpoint: str, owner_id: str) -> Dict[str, Any]:
        """Registers a new node in the Omega ecosystem."""
        node_data = {
            "node_id": node_id,
            "node_type": node_type,
            "endpoint": endpoint,
            "owner_id": owner_id,
            "status": "ACTIVE",
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        }
        inserted_node = OmegaCloudDB.insert_node(node_data)
        if not inserted_node:
            logger.error(f"[SPAWN] Failed to register node {node_id}")
            return {"success": False, "message": "Failed to register node"}
        logger.info(f"[SPAWN] Node {node_id} registered successfully.")
        return {"success": True, "message": f"Node {node_id} registered successfully"}

    @staticmethod
    def get_node_status(node_id: str) -> Dict[str, Any]:
        """Retrieves the status of a registered node."""
        node = OmegaCloudDB.get_node(node_id)
        if node:
            return {"success": True, "node": node}
        return {"success": False, "message": "Node not found"}

    @staticmethod
    def list_nodes() -> Dict[str, Any]:
        """Lists all registered nodes."""
        nodes = OmegaCloudDB.get_all_nodes()
        return {"success": True, "nodes": nodes}


# --- API Endpoints ---

@app.route("/v1/keys/generate", methods=["POST"])
@require_bearer_token
@check_permission("admin:generate_key")
def generate_key():
    data = request.get_json()
    if not data:
        abort(400, description="Request body must be JSON")

    owner_id = data.get("owner_id") 
    key_alias = data.get("key_alias")
    key_type = data.get("key_type", "BEARER")
    permissions = data.get("permissions", [])
    expires_in_days = data.get("expires_in_days")

    if not all([owner_id, key_alias]):
        abort(400, description="'owner_id' and 'key_alias' are required")
    
    if key_type not in ["BEARER", "HMAC"]:
        abort(400, description="'key_type' must be BEARER or HMAC")

    # Verify owner_id exists
    if not OmegaCloudDB.get_account(owner_id):
        abort(404, description=f"Owner with ID {owner_id} not found.")

    key_info = OmegaAuthSystem.generate_api_key(owner_id, key_alias, key_type, permissions, expires_in_days)
    logger.info(f"[API] Generated new {key_type} key for owner {owner_id} with alias {key_alias}")
    return jsonify(key_info), 201

@app.route("/v1/storage/objects", methods=["POST"])
@require_bearer_token # Or require_hmac_signature, depending on policy
@check_permission("storage:write")
def upload_object():
    owner_id = request.current_user["owner_id"]
    object_name = request.headers.get("X-Omega-Object-Name")
    content_type = request.headers.get("Content-Type", "application/octet-stream")
    is_immutable = request.headers.get("X-Omega-Immutable", "false").lower() == "true"
    metadata_str = request.headers.get("X-Omega-Metadata")
    metadata = None
    if metadata_str:
        try:
            metadata = json.loads(metadata_str)
        except json.JSONDecodeError:
            abort(400, description="X-Omega-Metadata header must be valid JSON")

    if not object_name:
        abort(400, description="X-Omega-Object-Name header is required")

    content = request.get_data()
    if not content:
        abort(400, description="Request body cannot be empty")

    uploaded_metadata = OmegaStorageEngine.upload_object(
        owner_id=owner_id,
        object_name=object_name,
        content=content,
        content_type=content_type,
        is_immutable=is_immutable,
        metadata=metadata
    )

    if uploaded_metadata:
        # Post event to ledger for auditability
        OmegaLedgerIntegration.post_event(
            event_type=EventType.OBJECT_UPLOADED,
            aggregate_id=uploaded_metadata["object_id"],
            aggregate_type="storage_object",
            owner_id=owner_id,
            event_data={"object_name": object_name, "size_bytes": uploaded_metadata["size_bytes"], "checksum": uploaded_metadata["checksum"]}
        )
        logger.info(f"[API] Object {uploaded_metadata["object_id"]} uploaded by owner {owner_id}")
        return jsonify({"message": "Object uploaded successfully", "object_id": uploaded_metadata["object_id"]}), 201
    logger.error(f"[API] Failed to upload object for owner {owner_id}")
    abort(500, description="Failed to upload object")

@app.route("/v1/storage/objects/<object_id>", methods=["GET"])
@require_bearer_token # Or require_hmac_signature
@check_permission("storage:read")
def download_object(object_id):
    owner_id = request.current_user["owner_id"]

    content = OmegaStorageEngine.download_object(object_id, owner_id)

    if content:
        metadata = OmegaCloudDB.get_storage_metadata(object_id)
        if metadata:
            # Post event to ledger for auditability
            OmegaLedgerIntegration.post_event(
                event_type=EventType.OBJECT_DOWNLOADED,
                aggregate_id=object_id,
                aggregate_type="storage_object",
                owner_id=owner_id,
                event_data={"object_name": metadata["object_name"], "size_bytes": metadata["size_bytes"]}
            )
            logger.info(f"[API] Object {object_id} downloaded by owner {owner_id}")
            return content, 200, {"Content-Type": metadata["content_type"], "X-Omega-Object-Name": metadata["object_name"]}
        logger.error(f"[API] Metadata not found for object {object_id} after successful download.")
        return content, 200, {"Content-Type": "application/octet-stream"}
    abort(404, description="Object not found or unauthorized")

@app.route("/v1/replication/objects/<object_id>", methods=["POST"])
@require_hmac_signature # Replication should use HMAC for integrity
@check_permission("storage:replicate")
def replicate_object(object_id):
    owner_id = request.current_user["owner_id"]
    data = request.get_json()
    if not data:
        abort(400, description="Request body must be JSON")

    target_nodes = data.get("target_nodes")

    if not target_nodes or not isinstance(target_nodes, list) or not all(isinstance(n, str) for n in target_nodes):
        abort(400, description="'target_nodes' (list of node names) is required and must be strings")
    
    replication_result = OmegaReplicationBridge.replicate_object(object_id, owner_id, target_nodes)
    if replication_result["success"]:
        # Post event to ledger for auditability
        OmegaLedgerIntegration.post_event(
            event_type=EventType.OBJECT_REPLICATED,
            aggregate_id=object_id,
            aggregate_type="storage_object",
            owner_id=owner_id,
            event_data={"target_nodes": target_nodes, "status": replication_result["replication_status"]}
        )
        logger.info(f"[API] Replication initiated for object {object_id} to {target_nodes} by owner {owner_id}")
        return jsonify({"message": "Replication initiated", "status": replication_result["replication_status"]}), 202
    logger.error(f"[API] Replication failed for object {object_id} by owner {owner_id}: {replication_result.get('message')}")
    abort(500, description=replication_result.get("message", "Replication failed"))

@app.route("/v1/ledger/transactions", methods=["POST"])
@require_hmac_signature # Financial transactions should use HMAC
@check_permission("ledger:post_transaction")
def post_ledger_transaction():
    owner_id = request.current_user["owner_id"]

    data = request.get_json()
    if not data:
        abort(400, description="Request body must be JSON")

    wallet_id = data.get("wallet_id")
    amount = data.get("amount")
    currency = data.get("currency", "USD")
    memo = data.get("memo", "API Transaction")

    if not all([wallet_id, amount]):
        abort(400, description="'wallet_id' and 'amount' are required")
    if not isinstance(amount, (int, float)) or amount <= 0:
        abort(400, description="Amount must be a positive number")

    result = OmegaLedgerIntegration.post_transaction(owner_id, wallet_id, float(amount), currency, memo)
    if result["success"]:
        logger.info(f"[API] Ledger transaction {result.get('transaction_id')} posted by owner {owner_id}")
        return jsonify(result), 201
    logger.error(f"[API] Failed to post ledger transaction for owner {owner_id}: {result.get('message')}")
    abort(500, description=result.get("message", "Failed to post transaction"))

@app.route("/v1/ledger/transactions/<transaction_id>", methods=["GET"])
@require_bearer_token
@check_permission("ledger:read_transaction_details")
def get_transaction_details(transaction_id):
    owner_id = request.current_user["owner_id"]
    result = OmegaLedgerIntegration.get_transaction_details(owner_id, transaction_id)
    if result["success"]:
        logger.info(f"[API] Transaction details for {transaction_id} retrieved by owner {owner_id}")
        return jsonify(result), 200
    abort(404, description=result.get("message", "Transaction not found or unauthorized"))

@app.route("/v1/ledger/wallets/<wallet_id>/balance", methods=["GET"])
@require_bearer_token # Or HMAC, depending on sensitivity
@check_permission("ledger:read_balance")
def get_wallet_balance(wallet_id):
    owner_id = request.current_user["owner_id"]
    
    result = OmegaLedgerIntegration.get_wallet_balance(owner_id, wallet_id)
    if result["success"]:
        logger.info(f"[API] Wallet balance for {wallet_id} retrieved by owner {owner_id}")
        return jsonify(result), 200
    logger.error(f"[API] Failed to retrieve wallet balance for {wallet_id} by owner {owner_id}: {result.get('message')}")
    abort(404, description=result.get("message", "Failed to retrieve balance"))

@app.route("/v1/ledger/wallets/<wallet_id>/history", methods=["GET"])
@require_bearer_token
@check_permission("ledger:read_history")
def get_wallet_history(wallet_id):
    owner_id = request.current_user["owner_id"]
    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")
    event_type = request.args.get("event_type")
    limit = int(request.args.get("limit", 100))

    history = OmegaLedgerIntegration.get_ledger_history(owner_id, aggregate_id=wallet_id, aggregate_type="wallet",
                                                       event_type=event_type, start_time=start_time, end_time=end_time, limit=limit)
    logger.info(f"[API] Wallet history for {wallet_id} retrieved by owner {owner_id}")
    return jsonify(history), 200

@app.route("/v1/ledger/audit", methods=["GET"])
@require_bearer_token
@check_permission("admin:read_audit_report")
def get_ledger_audit_report():
    # No owner_id filter here, as it's a system-wide audit report
    report = OmegaLedgerIntegration.get_system_audit_report()
    logger.info(f"[API] System-wide ledger audit report generated.")
    return jsonify(report), 200

@app.route("/v1/nodes/register", methods=["POST"])
@require_hmac_signature # Node registration should be highly secure
@check_permission("spawn_engine:register_node")
def register_node():
    owner_id = request.current_user["owner_id"]

    data = request.get_json()
    if not data:
        abort(400, description="Request body must be JSON")

    node_id = data.get("node_id")
    node_type = data.get("node_type")
    endpoint = data.get("endpoint")

    if not all([node_id, node_type, endpoint]):
        abort(400, description="'node_id', 'node_type', and 'endpoint' are required")

    result = OmegaSpawnEngine.register_node(node_id, node_type, endpoint, owner_id)
    if result["success"]:
        # Post event to ledger for auditability
        OmegaLedgerIntegration.post_event(
            event_type=EventType.NODE_REGISTERED,
            aggregate_id=node_id,
            aggregate_type="node",
            owner_id=owner_id,
            event_data={"node_type": node_type, "endpoint": endpoint}
        )
        logger.info(f"[API] Node {node_id} registered by owner {owner_id}")
        return jsonify(result), 201
    logger.error(f"[API] Failed to register node {node_id} by owner {owner_id}: {result.get('message')}")
    abort(500, description=result.get("message", "Failed to register node"))

@app.route("/v1/nodes/<node_id>", methods=["GET"])
@require_bearer_token
@check_permission("spawn_engine:read_node_status")
def get_node_status(node_id):
    owner_id = request.current_user["owner_id"]

    result = OmegaSpawnEngine.get_node_status(node_id)
    if result["success"]:
        # In a real system, filter node data based on owner_id for security
        logger.info(f"[API] Node status for {node_id} retrieved by owner {owner_id}")
        return jsonify(result["node"]), 200
    logger.error(f"[API] Node {node_id} not found for owner {owner_id}: {result.get('message')}")
    abort(404, description=result.get("message", "Node not found"))

@app.route("/v1/nodes", methods=["GET"])
@require_bearer_token
@check_permission("spawn_engine:list_nodes")
def list_nodes():
    owner_id = request.current_user["owner_id"]

    result = OmegaSpawnEngine.list_nodes()
    if result["success"]:
        # In a real system, filter nodes by owner_id or accessible nodes
        logger.info(f"[API] Node list retrieved by owner {owner_id}")
        return jsonify(result["nodes"]), 200
    logger.error(f"[API] Failed to list nodes for owner {owner_id}: {result.get('message')}")
    abort(500, description=result.get("message", "Failed to list nodes"))


# --- Main execution for running the Flask app ---
if __name__ == "__main__":
    migrate_db() # Ensure database schema is up-to-date
    logger.info(f"\n--- Starting Omega Cloud API Server on port {API_SERVER_PORT} ---")
    
    # For demonstration, we'll ensure a default owner exists and generate API keys for them
    default_owner_name = "MegaBankAdmin"
    default_owner = OmegaCloudDB.get_account_by_name(default_owner_name)
    if not default_owner:
        default_owner_id = str(uuid.uuid4())
        OmegaCloudDB.insert_account({"account_id": default_owner_id, "account_name": default_owner_name, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()})
        default_owner = OmegaCloudDB.get_account(default_owner_id)
        logger.info(f"[DEMO] Created default owner: {default_owner_name} with ID: {default_owner_id}")
    else:
        default_owner_id = default_owner["account_id"]
        logger.info(f"[DEMO] Using existing default owner: {default_owner_name} with ID: {default_owner_id}")

    # Generate a demo Bearer token for this owner
    from database import get_db_connection
    _c = get_db_connection().cursor()
    _c.execute("SELECT api_key_hash FROM omega_api_keys WHERE owner_id=? AND key_alias=?", (default_owner_id, "demo_bearer_token"))
    if not _c.fetchone():
        demo_bearer_key_info = OmegaAuthSystem.generate_api_key(
            owner_id=default_owner_id,
            key_alias="demo_bearer_token",
            key_type="BEARER",
            permissions=["storage:read", "storage:write", "ledger:post_transaction", "ledger:read_balance", "ledger:read_history", "spawn_engine:read_node_status", "spawn_engine:list_nodes", "ledger:read_transaction_details", "admin:read_audit_report", "admin:generate_key"],
            expires_in_days=365
        )
        logger.info(f"[DEMO] Bearer Token for {default_owner_id}: {demo_bearer_key_info['api_key']}")
    else:
        logger.info(f"[DEMO] Bearer token already exists for {default_owner_id}")

    # Generate a demo HMAC key for this owner
    _c2 = get_db_connection().cursor()
    _c2.execute("SELECT key_id FROM omega_api_keys WHERE owner_id=? AND key_alias=?", (default_owner_id, "demo_hmac_key"))
    if not _c2.fetchone():
        demo_hmac_key_info = OmegaAuthSystem.generate_api_key(
            owner_id=default_owner_id,
            key_alias="demo_hmac_key",
            key_type="HMAC",
            permissions=["storage:read", "storage:write", "storage:replicate", "ledger:post_transaction", "spawn_engine:register_node"],
            expires_in_days=365
        )
        logger.info(f"[DEMO] HMAC key created for {default_owner_id}")
    else:
        logger.info(f"[DEMO] HMAC key already exists for {default_owner_id}")

    # Initialize a dummy wallet for the owner if it doesn't exist
    if not OmegaCloudDB.get_wallet(f"wallet_{default_owner_id}"):
        OmegaCloudDB.update_wallet_balance_db(f"wallet_{default_owner_id}", 1000.0, default_owner_id)
        logger.info(f"[DEMO] Initialized wallet_id: wallet_{default_owner_id} with balance 1000.0")
    else:
        logger.info(f"[DEMO] Wallet wallet_{default_owner_id} already exists.")

    # Register a dummy node for consensus simulation
    if not OmegaCloudDB.get_node("node1_simulated"):
        OmegaSpawnEngine.register_node("node1_simulated", "phone_node", "http://localhost:5001", default_owner_id)
        logger.info("[DEMO] Registered simulated node1_simulated for consensus.")
    if not OmegaCloudDB.get_node("node2_simulated"):
        OmegaSpawnEngine.register_node("node2_simulated", "phone_node", "http://localhost:5002", default_owner_id)
        logger.info("[DEMO] Registered simulated node2_simulated for consensus.")

    # Run the Flask app
    # In a production environment, use a WSGI server like Gunicorn:
    # gunicorn -w 4 -b 0.0.0.0:5000 omega_cloud_node3_api_server:app
    app.run(host="0.0.0.0", port=API_SERVER_PORT, debug=False, use_reloader=False)




