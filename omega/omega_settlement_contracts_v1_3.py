import json
import uuid
from datetime import datetime

REQUIRED_FIELDS = {
    "event_id",
    "event_type",
    "aggregate_id",
    "aggregate_type",
    "merchant_id",
    "wallet_id",
    "amount",
    "currency",
    "timestamp",
    "version",
    "idempotency_key",
    "payload"
}

def validate_event(event: dict):
    missing = REQUIRED_FIELDS - set(event.keys())
    if missing:
        raise ValueError(f"EVENT_SCHEMA_VIOLATION_MISSING_FIELDS: {missing}")

    if not isinstance(event["payload"], dict):
        raise ValueError("PAYLOAD_MUST_BE_DICT")

    return True


def normalize_event(event: dict) -> dict:
    """
    🔒 STAGE 1: validation-safe normalization ONLY
    (NO JSON encoding here)
    """

    normalized = {}

    for k, v in event.items():

        if isinstance(v, datetime):
            normalized[k] = v.isoformat()

        elif v is None:
            normalized[k] = str(uuid.uuid4())

        else:
            normalized[k] = v

    # enforce payload stays dict (CRITICAL)
    if isinstance(normalized.get("payload"), str):
        raise ValueError("PAYLOAD_ALREADY_SERIALIZED_ILLEGALLY")

    validate_event(normalized)

    return normalized


def serialize_for_db(event: dict) -> dict:
    """
    🔒 STAGE 2: ONLY for DB layer
    """

    out = {}

    for k, v in event.items():

        if isinstance(v, (dict, list)):
            out[k] = json.dumps(v)

        else:
            out[k] = v

    return out
