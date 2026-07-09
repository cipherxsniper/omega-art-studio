import json

def normalize_event(event):
    event_id, event_type, payload, event_hash = event

    if isinstance(payload, dict):
        payload = json.dumps(payload, sort_keys=True)

    return (event_id, event_type, payload, event_hash)
