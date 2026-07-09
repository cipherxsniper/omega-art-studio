import hashlib
import json


def compute_event_hash(event: dict) -> str:
    return hashlib.sha256(
        json.dumps(event, sort_keys=True, default=str).encode()
    ).hexdigest()


def compute_chain_hash(prev_hash: str, event_hash: str) -> str:
    return hashlib.sha256(
        (str(prev_hash) + str(event_hash)).encode()
    ).hexdigest()


def get_last_chain_hash(cur):
    cur.execute("""
        SELECT chain_hash
        FROM ledger_postings
        ORDER BY created_at DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    return row["chain_hash"] if row else "GENESIS"


def append_chained_ledger(cur, event: dict):

    prev = get_last_chain_hash(cur)
    event_hash = compute_event_hash(event)
    chain_hash = compute_chain_hash(prev, event_hash)

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
            event_hash,
            prev_hash,
            chain_hash
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
            %(event_hash)s,
            %(prev_hash)s,
            %(chain_hash)s
        )
        ON CONFLICT (event_id) DO NOTHING;
    """, {
        **event,
        "payload": json.dumps(event.get("payload", {})),
        "event_hash": event_hash,
        "prev_hash": prev,
        "chain_hash": chain_hash
    })

    return {
        "status": "CHAINED",
        "event_id": event["event_id"],
        "chain_hash": chain_hash
    }
