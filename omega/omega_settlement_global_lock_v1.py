from omega_db_kernel_v1 import OmegaTransaction
import hashlib
import json


# -----------------------------
# GLOBAL LOCK TABLE CHECK
# -----------------------------

def is_globally_locked(cur, event_id: str) -> bool:
    cur.execute("""
        SELECT 1
        FROM omega_settlement_global_lock
        WHERE event_id = %s
        LIMIT 1
    """, (event_id,))
    return cur.fetchone() is not None


# -----------------------------
# ACQUIRE GLOBAL LOCK (ATOMIC)
# -----------------------------

def acquire_lock(cur, event_id: str, hash_value: str):
    cur.execute("""
        INSERT INTO omega_settlement_global_lock (
            event_id,
            hash,
            locked_at
        )
        VALUES (%s, %s, NOW())
        ON CONFLICT (event_id) DO NOTHING;
    """, (event_id, hash_value))


# -----------------------------
# SAFE ENTRY POINT (ONLY ONE PATH NOW)
# -----------------------------

def settlement_gate(cur, event: dict):

    event_id = event["event_id"]

    # 1. HARD BLOCK IF LOCKED
    if is_globally_locked(cur, event_id):
        return {"status": "SKIPPED_GLOBAL_LOCKED"}

    # 2. LOCK BEFORE ANY WRITE
    h = hashlib.sha256(
        json.dumps(event, sort_keys=True, default=str).encode()
    ).hexdigest()

    acquire_lock(cur, event_id, h)

    # 3. WRITE SETTLEMENT EVENT (SAFE NOW)
    cur.execute("""
        INSERT INTO ledger_postings (
            event_id,
            aggregate_id,
            amount,
            account_type,
            direction,
            currency,
            timestamp,
            payload,
            hash
        )
        VALUES (
            %(event_id)s,
            %(aggregate_id)s,
            %(amount)s,
            'SETTLEMENT',
            'CREDIT',
            %(currency)s,
            %(timestamp)s,
            %(payload)s::jsonb,
            %(hash)s
        )
        ON CONFLICT (event_id) DO NOTHING;
    """, {
        **event,
        "payload": json.dumps(event.get("payload", {})),
        "hash": h
    })

    return {
        "status": "LOCKED_AND_COMMITTED",
        "event_id": event_id,
        "hash": h
    }
