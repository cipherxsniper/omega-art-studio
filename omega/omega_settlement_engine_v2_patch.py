from omega_settlement_contract_v2 import normalize_event
from omega_psycopg_adapter_v2 import safe_event
from omega_idempotency_guard_v2 import is_settled

def run_settlement(cur, events):
    results = []

    for event in events:

        # 1. contract enforcement
        event = normalize_event(event)

        # 2. idempotency gate
        if is_settled(cur, event["event_id"]):
            continue

        # 3. psycopg-safe transformation
        event = safe_event(event)

        # 4. insert safe event only
        cur.execute("""
            INSERT INTO ledger_postings (
                event_id,
                aggregate_id,
                sequence_number,
                account_type,
                direction,
                amount,
                currency,
                timestamp,
                payload,
                hash
            )
            VALUES (
                %(event_id)s,
                %(aggregate_id)s,
                %(sequence_number)s,
                %(aggregate_type)s,
                'CREDIT',
                COALESCE((payload->>'amount')::numeric, 0),
                %(currency)s,
                %(timestamp)s,
                %(payload)s,
                %(hash)s
            )
        """, event)

        results.append({
            "status": "SETTLED",
            "event_id": event["event_id"],
            "hash": event["hash"]
        })

    return results
