from omega_db_kernel_v1 import OmegaTransaction, insert_event
import uuid
import json
from datetime import datetime, UTC

STATE = {
    "PENDING": "PENDING",
    "SETTLED": "SETTLED",
    "FINALIZED": "FINALIZED",
    "SEALED": "SEALED"
}

SETTLEMENT_KEY = "OMEGA_GLOBAL_SETTLEMENT_V2"
SETTLEMENT_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, SETTLEMENT_KEY))

def safe(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [safe(v) for v in obj]
    return obj

def get_state(cur):
    cur.execute("""
        SELECT state FROM omega_settlement_state
        WHERE settlement_id = %s
        ORDER BY updated_at DESC
        LIMIT 1
    """, (SETTLEMENT_ID,))
    row = cur.fetchone()
    return row["state"] if row else STATE["PENDING"]

def set_state(cur, state):
    cur.execute("""
        INSERT INTO omega_settlement_state (
            id, settlement_id, state, payload, updated_at
        ) VALUES (%s,%s,%s,%s,NOW())
    """, (
        str(uuid.uuid4()),
        SETTLEMENT_ID,
        state,
        json.dumps({"state": state})
    ))

def already_finalized(cur):
    cur.execute("""
        SELECT 1 FROM ledger_postings
        WHERE event_id = %s
        AND account_type = 'SETTLEMENT_FINALIZED'
        LIMIT 1
    """, (SETTLEMENT_ID,))
    return cur.fetchone() is not None

def run_state_machine(cur):

    state = get_state(cur)

    if state == STATE["SEALED"]:
        return {"status": "SEALED_NO_OP"}

    if state == STATE["PENDING"]:
        set_state(cur, STATE["PENDING"])

    if state == STATE["SETTLED"]:
        set_state(cur, STATE["SETTLED"])

    if state == STATE["FINALIZED"]:
        if already_finalized(cur):
            return {"status": "IDEMPOTENT_FINALIZED"}
        set_state(cur, STATE["FINALIZED"])

        cur.execute("""
            INSERT INTO ledger_postings (
                posting_id,
                event_id,
                sequence_number,
                account_type,
                account_id,
                direction,
                amount,
                currency
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            str(uuid.uuid4()),
            SETTLEMENT_ID,
            999999,
            "SETTLEMENT_FINALIZED",
            None,
            "CREDIT",
            0,
            "USD"
        ))

        set_state(cur, STATE["SEALED"])
        return {"status": "SEALED"}

    return {"status": state}

if __name__ == "__main__":
    with OmegaTransaction() as cur:
        result = run_state_machine(cur)
        print(result)
