import json
from omega_settlement_contract_v2 import event_hash

def safe_event(event: dict) -> dict:
    event = dict(event)

    # force payload to JSON string for DB safety
    event["payload"] = json.dumps(event["payload"], sort_keys=True)

    # attach immutable hash
    event["hash"] = event_hash(event)

    return event
