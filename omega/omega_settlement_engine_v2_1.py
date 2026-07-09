from omega_db_kernel_v1 import OmegaTransaction, insert_event
from omega_settlement_state_machine_v1 import get_state, STATE
from omega_event_chain_v1 import EventChain
from omega_idempotency_contract_v1 import is_settled, mark_settled
from omega_settlement_contracts_v1 import normalize_event
import uuid

chain = EventChain()

def run_settlement(cur):

    state = get_state(cur)

    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "SETTLEMENT_FINALIZED_V2",
        "aggregate_id": str(uuid.uuid4()),
        "aggregate_type": "SETTLEMENT",
        "merchant_id": "omega_settlement",
        "wallet_id": str(uuid.uuid4()),
        "amount": "0",
        "currency": "USD",
        "timestamp": "NOW",
        "version": 2,
        "idempotency_key": str(uuid.uuid4()),
        "payload": {
            "state": state
        }
    }

    # 🔒 NORMALIZE FIRST
    event = normalize_event(event)

    # 🔒 IDEMPOTENCY CHECK
    if is_settled(cur, event["event_id"]):
        return {"status": "SKIPPED_DUPLICATE"}

    # 🔗 HASH CHAIN ATTACHMENT
    chained = chain.link(event)
    event["chain_hash"] = chained["hash"]

    # 🔥 WRITE EVENT
    insert_event(cur, event)

    # 🔒 MARK IDEMPOTENT
    mark_settled(cur, event)

    return {
        "status": "SETTLED",
        "event_id": event["event_id"],
        "hash": event["chain_hash"]
    }

if __name__ == "__main__":
    with OmegaTransaction() as cur:
        print(run_settlement(cur))
