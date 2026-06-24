import json
from omega_db_kernel_v1 import OmegaTransaction

def is_settled(cur, event_id):
    cur.execute("""
        SELECT 1
        FROM omega_idempotency_log
        WHERE event_id = %s
        LIMIT 1
    """, (event_id,))
    return cur.fetchone() is not None


def _safe_json(v):
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    return v


def mark_settled(cur, event):

    # 🔒 HARD FIX: sanitize EVERYTHING BEFORE INSERT

    safe_payload = _safe_json(event.get("payload"))

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
            %(idempotency_key)s,
            %(event_type)s,
            %(payload)s,
            NOW()
        )
    """, {
        "event_id": event["event_id"],
        "idempotency_key": event.get("idempotency_key"),
        "event_type": event["event_type"],
        "payload": safe_payload
    })
