#!/usr/bin/env python3
"""
=========================================================
OMEGA CORE CONTRACT v1 — CANONICAL SYSTEM BOUNDARY
=========================================================

This module defines the SINGLE SOURCE OF TRUTH for:
- Settlement execution
- Ledger writes
- Event normalization
- Idempotency enforcement

NO OTHER MODULE MAY WRITE TO LEDGER OR SETTLEMENT STATE DIRECTLY.
ALL WRITES MUST FLOW THROUGH THIS CONTRACT.
=========================================================
"""

import json
import hashlib
import datetime


# =========================
# CORE NORMALIZATION LAYER
# =========================

def normalize_payload(event: dict) -> dict:
    """
    Ensures ALL events are canonical dict format with safe serialization.
    """

    if not isinstance(event, dict):
        raise ValueError("PAYLOAD_MUST_BE_DICT")

    normalized = {}

    for k, v in event.items():
        if isinstance(v, (datetime.datetime, datetime.date)):
            normalized[k] = v.isoformat()
        elif isinstance(v, dict):
            normalized[k] = json.dumps(v, default=str)
        else:
            normalized[k] = v

    return normalized


# =========================
# IDEMPOTENCY KEY BUILDER
# =========================

def build_idempotency_key(event: dict) -> str:
    """
    Deterministic idempotency key generator.
    """

    core = json.dumps(event, sort_keys=True, default=str)
    return hashlib.sha256(core.encode()).hexdigest()


# =========================
# LEDGER HASH CHAIN
# =========================

def compute_ledger_hash(previous_hash: str, event: dict) -> str:
    """
    Cryptographic chaining of ledger entries.
    """

    payload = json.dumps(event, sort_keys=True, default=str)
    combined = f"{previous_hash}:{payload}"
    return hashlib.sha256(combined.encode()).hexdigest()


# =========================
# EVENT VALIDATION GATE
# =========================

def validate_event(event: dict):
    """
    Hard validation gate — NO INVALID EVENTS ENTER SYSTEM.
    """

    if not isinstance(event, dict):
        raise ValueError("PAYLOAD_MUST_BE_DICT")

    required_fields = ["event_id", "type", "payload"]

    for f in required_fields:
        if f not in event:
            raise ValueError(f"MISSING_FIELD:{f}")


# =========================
# CANONICAL WRAP FUNCTION
# =========================

def canonicalize_event(event: dict) -> dict:
    """
    Full canonical transformation pipeline.
    """

    validate_event(event)

    event = normalize_payload(event)

    event["idempotency_key"] = build_idempotency_key(event)

    return event


# =========================
# LEDGER WRITER CONTRACT
# =========================

def write_to_ledger(cur, event: dict, previous_hash: str):
    """
    ONLY allowed ledger write entry point.
    """

    event = canonicalize_event(event)

    ledger_hash = compute_ledger_hash(previous_hash, event)

    cur.execute(
        """
        INSERT INTO omega_ledger_chain (
            event_id,
            payload,
            idempotency_key,
            ledger_hash,
            previous_hash,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (event_id) DO NOTHING;
        """,
        (
            event["event_id"],
            json.dumps(event, default=str),
            event["idempotency_key"],
            ledger_hash,
            previous_hash
        )
    )

    return {
        "status": "WRITTEN",
        "ledger_hash": ledger_hash
    }


# =========================
# CONTRACT EXPORTS ONLY
# =========================

__all__ = [
    "normalize_payload",
    "build_idempotency_key",
    "compute_ledger_hash",
    "validate_event",
    "canonicalize_event",
    "write_to_ledger"
]
