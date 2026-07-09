from omega_db_kernel_v1 import OmegaTransaction, insert_event
import uuid

def has_run(cur, settlement_id):
    cur.execute("""
        SELECT 1 FROM omega_events
        WHERE event_type = 'SETTLEMENT_FINALIZED_V2'
        AND aggregate_id = %s
        LIMIT 1
    """, (settlement_id,))
    return cur.fetchone() is not None


def safe_settlement(cur, settlement_id, build_fn):
    if has_run(cur, settlement_id):
        return {"status": "SKIPPED", "reason": "idempotent_replay_blocked"}

    events = build_fn()

    for e in events:
        insert_event(cur, e)

    return {"status": "COMMITTED", "events": len(events)}


if __name__ == "__main__":
    with OmegaTransaction() as cur:
        sid = str(uuid.uuid4())
        result = safe_settlement(cur, sid, lambda: [])
        print(result)
