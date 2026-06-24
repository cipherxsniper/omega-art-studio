"""
OMEGA SETTLEMENT ABSTRACTION LAYER V1
Ledger-first settlement engine (NO REAL MONEY ASSUMPTIONS)

Single Source of Truth:
    ledger_events table only

This layer defines:
- settlement intents
- external mapping abstraction (Stripe placeholder only)
- deterministic replay-safe settlement execution
"""

import time
import json
import hashlib
from omega_event_bus_core_v1 import connect_db

# ----------------------------
# SETTLEMENT INTENT TYPES
# ----------------------------
DEBIT = "DEBIT"
CREDIT = "CREDIT"
SETTLE = "SETTLE"
RESERVE = "RESERVE"

# ----------------------------
# SETTLEMENT ENGINE CORE
# ----------------------------
def generate_tx_id(prefix="SETTLE"):
    raw = f"{prefix}_{time.time()}_{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]}"
    return raw


def compute_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


# ----------------------------
# CORE SETTLEMENT FUNCTION
# ----------------------------
def execute_settlement(conn, from_account, to_account, amount, metadata=None):
    """
    Ledger-only deterministic settlement.

    NO external liquidity assumptions.
    """

    metadata = metadata or {}
    tx_id = generate_tx_id("SETTLE")

    cur = conn.cursor()

    # debit
    cur.execute("""
        INSERT INTO ledger_events (
            account_id, event_type, amount, tx_id, timestamp
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        from_account,
        "SETTLEMENT_DEBIT",
        -abs(amount),
        tx_id,
        time.time()
    ))

    # credit
    cur.execute("""
        INSERT INTO ledger_events (
            account_id, event_type, amount, tx_id, timestamp
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        to_account,
        "SETTLEMENT_CREDIT",
        abs(amount),
        tx_id,
        time.time()
    ))

    conn.commit()

    return {
        "tx_id": tx_id,
        "from": from_account,
        "to": to_account,
        "amount": amount,
        "status": "SETTLED"
    }


# ----------------------------
# STRIPE MAPPING (SANDBOX ONLY)
# ----------------------------
def map_stripe_to_ledger(stripe_customer_id):
    """
    External wallet mapping layer (Stripe ONLY for now)

    DO NOT treat as real banking identity.
    """
    return f"STRIPE::{stripe_customer_id}"


# ----------------------------
# REPLAY SAFE SETTLEMENT CHECK
# ----------------------------
def settlement_exists(conn, tx_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM ledger_events WHERE tx_id = ?
    """, (tx_id,))
    return cur.fetchone() is not None


# ----------------------------
# SAFE ENTRYPOINT
# ----------------------------
def settle_if_not_exists(conn, from_acc, to_acc, amount, tx_id_hint=None):
    tx_id = tx_id_hint or generate_tx_id()

    if settlement_exists(conn, tx_id):
        print("[SETTLEMENT SKIP] already exists:", tx_id)
        return None

    return execute_settlement(conn, from_acc, to_acc, amount)
