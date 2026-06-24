from omega_db_kernel_v1 import OmegaTransaction
import json
import hashlib


# -----------------------------
# STRICT EVENT NORMALIZER
# -----------------------------

def canonical_event(event: dict) -> dict:
    """
    Forces event into strict schema BEFORE ANY DB TOUCH.
    """

    return {
        "event_id": event["event_id"],
        "event_type": str(event["event_type"]),
        "aggregate_id": str(event.get("aggregate_id", "")),
        "amount": float(event.get("amount", 0)),
        "currency": event.get("currency", "USD"),
        "timestamp": str(event.get("timestamp")),
        "payload": event.get("payload") if isinstance(event.get("payload"), dict) else {}
    }


# -----------------------------
# STRICT IDEMPOTENCY GATE
# -----------------------------

def already_committed(cur, event_id: str) -> bool:
    cur.execute("""
        SELECT 1 FROM omega_idempotency_log
        WHERE event_id = %s
        LIMIT 1
    """, (event_id,))
    return cur.fetchone() is not None


# -----------------------------
# HASH LOCK (ANTI-DOUBLE WRITE)
# -----------------------------

def event_hash(event: dict) -> str:
    return hashlib.sha256(
        json.dumps(event, sort_keys=True, default=str).encode()
    ).hexdigest()


# -----------------------------
# HARD SETTLEMENT WRITE GATE
# -----------------------------

def write_settlement(cur, event: dict):

    event = canonical_event(event)

    # BLOCK DUPLICATES BEFORE INSERT
    if already_committed(cur, event["event_id"]):
        return {"status": "SKIPPED_DUPLICATE"}

    h = event_hash(event)

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
        ) VALUES (
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
        "payload": json.dumps(event["payload"]),
        "hash": h
    })

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
            %(event_id)s,
            %(hash)s,
            %(event_type)s,
            %(payload)s::jsonb,
            NOW()
        )
        ON CONFLICT (event_id) DO NOTHING;
    """, {
        "event_id": event["event_id"],
        "hash": h,
        "event_type": event["event_type"],
        "payload": json.dumps(event["payload"])
    })

    return {"status": "COMMITTED", "hash": h}


# -----------------------------
# FINALITY ENFORCER
# -----------------------------

def enforce_finality(cur):
    """
    Ensures settlement ledger cannot drift post-write.
    """

    cur.execute("""
        SELECT event_id, COUNT(*)
        FROM ledger_postings
        WHERE account_type = 'SETTLEMENT'
        GROUP BY event_id
        HAVING COUNT(*) > 1
    """)

    violations = cur.fetchall()

    if violations:
        raise Exception(f"LEDGER_FINALITY_BREACH: {violations}")

    return {"status": "FINALITY_OK"}
