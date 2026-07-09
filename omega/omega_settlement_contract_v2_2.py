import json
import hashlib
from datetime import datetime

REQUIRED_FIELDS = {
    "event_id",
    "event_type",
    "aggregate_id",
    "aggregate_type",
    "payload",
    "sequence_number",
    "timestamp",
    "version"
}

def normalize_event(event: dict) -> dict:
    if not isinstance(event, dict):
        raise ValueError("EVENT_MUST_BE_DICT")

    # enforce required structure
    missing = REQUIRED_FIELDS - set(event.keys())
    if missing:
        raise ValueError(f"MISSING_FIELDS:{missing}")

    # ensure payload is JSON-safe dict
    if not isinstance(event["payload"], dict):
        raise ValueError("PAYLOAD_MUST_BE_DICT")

    # normalize timestamp
    if isinstance(event["timestamp"], datetime):
        event["timestamp"] = event["timestamp"].isoformat()

    return event


def event_hash(event: dict) -> str:
    canonical = json.dumps(event, sort_keys=True, default=str).encode()
    return hashlib.sha256(canonical).hexdigest()
