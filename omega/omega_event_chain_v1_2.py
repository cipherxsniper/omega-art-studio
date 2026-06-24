import hashlib
import json
from datetime import datetime

def canonical(event: dict) -> str:
    """
    Stable serialization for hashing
    """
    return json.dumps(event, sort_keys=True, default=str)


def compute_hash(event: dict, prev_hash: str | None) -> str:
    payload = {
        "event": event,
        "prev_hash": prev_hash or "GENESIS"
    }
    data = canonical(payload).encode()
    return hashlib.sha256(data).hexdigest()


class EventChain:
    def __init__(self):
        self.last_hash = None

    def link(self, event: dict):
        h = compute_hash(event, self.last_hash)
        self.last_hash = h
        return {
            "event": event,
            "hash": h,
            "prev_hash": None if not self.last_hash else self.last_hash
        }
