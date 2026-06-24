import redis
import json
import uuid
import time

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

STREAM = "omega:events"

def publish(event_type, payload, idempotency_key=None):
    event = {
        "event_id": str(uuid.uuid4()),
        "type": event_type,
        "payload": json.dumps(payload),
        "idempotency_key": idempotency_key or str(uuid.uuid4()),
        "ts": time.time()
    }

    r.xadd(STREAM, event)
    return event
