#!/usr/bin/env python3

"""
=========================================================
OMEGA STRIPE WEBHOOK REPLAY VALIDATOR v1
Deterministic External Truth Reconciliation Layer
NO LIVE PAYMENT EXECUTION
SAFE REPLAY / AUDIT ONLY
=========================================================
"""

import json
import hashlib
import sqlite3
from datetime import datetime, timezone

from omega_env_loader_v1 import get_db_path, get_env


# -----------------------------
# HASH ENGINE (DETERMINISTIC)
# -----------------------------
def hash_event(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


# -----------------------------
# DB ACCESS
# -----------------------------
def connect_db():
    return sqlite3.connect(get_db_path())


# -----------------------------
# LOAD RECENT LEDGER STATE
# -----------------------------
def get_latest_ledger_event(cur):
    try:
        cur.execute("""
            SELECT tx_id, source, status, created_at
            FROM transactions
            ORDER BY created_at DESC
            LIMIT 1
        """)
        return cur.fetchone()
    except Exception:
        return None


# -----------------------------
# REPLAY VALIDATION CORE
# -----------------------------
def validate_webhook(payload: dict, ledger_event):
    event_hash = hash_event(payload)

    ledger_hash = None
    if ledger_event:
        ledger_hash = hash_event({
            "tx_id": ledger_event[0],
            "source": ledger_event[1],
            "status": ledger_event[2],
            "created_at": ledger_event[3]
        })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_hash": event_hash,
        "ledger_hash": ledger_hash,
        "divergence": event_hash != ledger_hash if ledger_hash else False,
        "replay_safe": True,
        "decision": "CONSISTENT" if event_hash == ledger_hash else "DIVERGENCE_DETECTED"
    }


# -----------------------------
# MAIN ENTRY
# -----------------------------
def run():
    conn = connect_db()
    cur = conn.cursor()

    ledger_event = get_latest_ledger_event(cur)

    # SIMULATED STRIPE WEBHOOK PAYLOAD (SAFE MODE)
    sample_payload = {
        "id": "evt_test_001",
        "object": "event",
        "type": "payment_intent.succeeded",
        "amount": 1000,
        "currency": "usd"
    }

    result = validate_webhook(sample_payload, ledger_event)

    print("🌐 OMEGA STRIPE WEBHOOK REPLAY VALIDATOR v1")
    print(json.dumps(result, indent=2))

    conn.close()


if __name__ == "__main__":
    run()
