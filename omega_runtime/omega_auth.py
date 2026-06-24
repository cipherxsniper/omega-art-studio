#!/usr/bin/env python3
"""
OMEGA CLOUD — AUTH ENGINE
Bearer tokens + HMAC-v2 signing.
No external deps. Pure Python.
"""
import os
import json
import hashlib
import hmac as hmac_lib
import secrets
from datetime import datetime, timezone, timedelta

AUTH_DIR = os.path.expanduser("~/omega_runtime/auth")
os.makedirs(AUTH_DIR, exist_ok=True)

KEYS_FILE = os.path.join(AUTH_DIR, "api_keys.json")

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _hash(val: str) -> str:
    return hashlib.sha256(val.encode()).hexdigest()

def _load_keys() -> dict:
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE) as f:
            return json.load(f)
    return {}

def _save_keys(keys: dict):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)
    os.chmod(KEYS_FILE, 0o600)

class OmegaAuth:

    @staticmethod
    def generate_bearer(owner_id: str, alias: str,
                        permissions: list = None,
                        expires_days: int = 365) -> dict:
        keys     = _load_keys()
        raw_key  = secrets.token_urlsafe(32)
        key_hash = _hash(raw_key)
        key_id   = secrets.token_hex(8)
        expires  = (datetime.now(timezone.utc) +
                    timedelta(days=expires_days)).isoformat()

        keys[key_hash] = {
            "key_id":      key_id,
            "owner_id":    owner_id,
            "alias":       alias,
            "type":        "BEARER",
            "permissions": permissions or ["storage:read","storage:write"],
            "status":      "ACTIVE",
            "created_at":  _now(),
            "expires_at":  expires,
        }
        _save_keys(keys)
        return {
            "key_id":    key_id,
            "api_key":   raw_key,
            "owner_id":  owner_id,
            "expires_at": expires,
        }

    @staticmethod
    def generate_hmac(owner_id: str, alias: str,
                      permissions: list = None,
                      expires_days: int = 365) -> dict:
        keys       = _load_keys()
        raw_key    = secrets.token_urlsafe(32)
        raw_secret = secrets.token_urlsafe(64)
        key_hash   = _hash(raw_key)
        sec_hash   = _hash(raw_secret)
        key_id     = secrets.token_hex(8)
        expires    = (datetime.now(timezone.utc) +
                      timedelta(days=expires_days)).isoformat()

        keys[key_hash] = {
            "key_id":      key_id,
            "owner_id":    owner_id,
            "alias":       alias,
            "type":        "HMAC",
            "secret_hash": sec_hash,
            "permissions": permissions or ["storage:read","storage:write","storage:replicate"],
            "status":      "ACTIVE",
            "created_at":  _now(),
            "expires_at":  expires,
        }
        _save_keys(keys)
        return {
            "key_id":     key_id,
            "api_key":    raw_key,
            "api_secret": raw_secret,
            "owner_id":   owner_id,
            "expires_at": expires,
        }

    @staticmethod
    def verify_bearer(api_key: str) -> tuple:
        """Returns (owner_id, permissions) or (None, None)."""
        keys     = _load_keys()
        key_hash = _hash(api_key)
        record   = keys.get(key_hash)
        if not record:
            return None, None
        if record["status"] != "ACTIVE":
            return None, None
        if record["type"] != "BEARER":
            return None, None
        expires = datetime.fromisoformat(record["expires_at"])
        if datetime.now(timezone.utc) > expires:
            return None, None
        return record["owner_id"], record["permissions"]

    @staticmethod
    def verify_hmac(api_key: str, api_secret: str,
                    method: str, path: str, body: bytes,
                    timestamp: str) -> tuple:
        """Returns (owner_id, permissions) or (None, None)."""
        keys     = _load_keys()
        key_hash = _hash(api_key)
        record   = keys.get(key_hash)
        if not record:
            return None, None
        if record["status"] != "ACTIVE":
            return None, None
        if record["type"] != "HMAC":
            return None, None
        expires = datetime.fromisoformat(record["expires_at"])
        if datetime.now(timezone.utc) > expires:
            return None, None

        # Verify timestamp within 5 minutes
        try:
            ts = datetime.fromisoformat(timestamp)
            delta = abs((datetime.now(timezone.utc) - ts).total_seconds())
            if delta > 300:
                return None, None
        except Exception:
            return None, None

        # Verify HMAC signature
        body_hash  = hashlib.sha256(body).hexdigest()
        msg        = f"{method}\n{path}\n{timestamp}\n{body_hash}"
        expected   = hmac_lib.new(
            record["secret_hash"].encode(),
            msg.encode(),
            hashlib.sha256
        ).hexdigest()
        if not hmac_lib.compare_digest(expected, _hash(api_secret)):
            return None, None

        return record["owner_id"], record["permissions"]

    @staticmethod
    def has_permission(permissions: list, required: str) -> bool:
        return required in permissions or "admin:all" in permissions

    @staticmethod
    def list_keys() -> list:
        keys = _load_keys()
        result = []
        for key_hash, record in keys.items():
            r = dict(record)
            r.pop("secret_hash", None)
            result.append(r)
        return sorted(result, key=lambda x: x["created_at"], reverse=True)

    @staticmethod
    def revoke(key_id: str) -> bool:
        keys = _load_keys()
        for key_hash, record in keys.items():
            if record["key_id"] == key_id:
                record["status"] = "REVOKED"
                _save_keys(keys)
                return True
        return False


if __name__ == "__main__":
    print("Testing Omega Auth Engine...")

    # Bearer
    bearer = OmegaAuth.generate_bearer(
        "thomas_lee_harvey", "admin_bearer",
        ["storage:read","storage:write","storage:delete",
         "admin:all"], 365
    )
    print(f"✅ Bearer generated: {bearer['key_id']}")

    owner, perms = OmegaAuth.verify_bearer(bearer["api_key"])
    assert owner == "thomas_lee_harvey"
    print(f"✅ Bearer verified: owner={owner}")

    # HMAC
    hmac_key = OmegaAuth.generate_hmac(
        "thomas_lee_harvey", "node_hmac",
        ["storage:replicate","ledger:write"], 365
    )
    print(f"✅ HMAC generated: {hmac_key['key_id']}")

    # List
    keys = OmegaAuth.list_keys()
    print(f"✅ Listed {len(keys)} keys")

    # Revoke
    OmegaAuth.revoke(bearer["key_id"])
    owner2, _ = OmegaAuth.verify_bearer(bearer["api_key"])
    assert owner2 is None
    print(f"✅ Revoke confirmed")

    print("\n🔐 Omega Auth Engine - ALL TESTS PASSED")
