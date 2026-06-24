import hashlib
import json
from omega_db_kernel_v1 import OmegaTransaction


# -----------------------------
# HASH FUNCTION
# -----------------------------

def hash_event(event: dict) -> str:
    return hashlib.sha256(
        json.dumps(event, sort_keys=True, default=str).encode()
    ).hexdigest()


# -----------------------------
# ATOMIC CHECK GATE
# -----------------------------

def already_exists(cur, event_id: str, hash_value: str) -> bool:
    cur.execute("""
        SELECT 1
        FROM omega_idempotency_log
        WHERE event_id = %s OR idempotency_key = %s
        LIMIT 1
    """, (event_id, hash_value))

    return cur.fetchone() is not None


def ledger_exists(cur, event_id: str) -> bool:
    cur.execute("""
        SELECT 1
        FROM ledger_postings
        WHERE event_id = %s
        LIMIT 1
    """, (event_id,))

    return cur.fetchone() is not None


# -----------------------------
# PURE ATOMIC WRITE GATE
# -----------------------------

def safe_settlement_write(cur, event: dict):

    event_hash = hash_event(event)

    # 1. IDENTITY CHECK
    if already_exists(cur, event["event_id"], event_hash):
        return {"status": "SKIPPED_IDEMPOTENT"}

    # 2. LEDGER CHECK (CRITICAL FIX)
    if ledger_exists(cur, event["event_id"]):
        return {"status": "SKIPPED_LEDGER_EXISTS"}

    # 3. SINGLE WRITE ONLY
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
    """, {
        **event,
        "payload": json.dumps(event.get("payload", {})),
        "hash": event_hash
    })

    # 4. IDEMPOTENCY COMMIT
    cur.execute("""
        INSERT INTO omega_idempotency_log (
            id,
            event_id,
            idempotency_key,
            event_type,
            payload,
            created_at
        )
        VALUES (
            gen_random_uuid(),
            %s,
            %s,
            %s,
            %s::jsonb,
            NOW()
        )
    """, (
        event["event_id"],
        event_hash,
        event["event_type"],
        json.dumps(event.get("payload", {}))
    ))

    return {
        "status": "COMMITTED",
        "event_id": event["event_id"],
        "hash": event_hash
    }
