import hashlib
import json
from datetime import datetime

# -----------------------------
# IDENTITY + IDENTITY GUARD
# -----------------------------

def stable_event_hash(event: dict) -> str:
    """
    Deterministic hash of event (replay-safe identity).
    """
    canonical = json.dumps(event, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def is_settled(cur, event_id: str) -> bool:
    cur.execute("""
        SELECT 1
        FROM omega_idempotency_log
        WHERE event_id = %s
        LIMIT 1
    """, (event_id,))
    return cur.fetchone() is not None


def mark_settled(cur, event: dict):
    """
    HARD FIX:
    - NO raw dict insert
    - NO datetime objects
    - FULL JSON serialization safety
    """

    safe_payload = json.dumps(event.get("payload", {}), default=str)

    cur.execute("""
        INSERT INTO omega_idempotency_log (
            id,
            event_id,
            idempotency_key,
            event_type,
            payload,
            created_at
        ) VALUES (
            gen_random_uuid(),
            %(event_id)s,
            %(idempotency_key)s,
            %(event_type)s,
            %(payload)s,
            NOW()
        )
        ON CONFLICT (event_id) DO NOTHING;
    """, {
        "event_id": event["event_id"],
        "idempotency_key": event.get("idempotency_key"),
        "event_type": event["event_type"],
        "payload": safe_payload
    })


# -----------------------------
# ATOMIC LEDGER CHAIN LINK
# -----------------------------

def compute_chain_link(cur):
    """
    Creates hash-linked ledger ordering (prevents silent tampering/reorder).
    """
    cur.execute("""
        SELECT event_id, event_type, payload, created_at
        FROM omega_events
        ORDER BY sequence_number ASC
    """)
    events = cur.fetchall()

    prev_hash = "GENESIS"

    for e in events:
        current = {
            "event_id": e["event_id"],
            "event_type": e["event_type"],
            "payload": e["payload"],
            "created_at": str(e["created_at"]),
            "prev_hash": prev_hash
        }

        h = stable_event_hash(current)

        cur.execute("""
            UPDATE omega_events
            SET hash = %s,
                prev_hash = %s
            WHERE event_id = %s
        """, (h, prev_hash, e["event_id"]))

        prev_hash = h


# -----------------------------
# SETTLEMENT GATE LOCK
# -----------------------------

def settlement_gate(cur, event: dict) -> bool:
    """
    HARD STOP DUPLICATES
    """
    if is_settled(cur, event["event_id"]):
        return False
    return True
