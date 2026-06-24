import json
import hashlib
import os

FREEZE_FILE = "core/.freeze_snapshot.json"


def hash_object(obj):
    raw = json.dumps(obj, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def save_snapshot(snapshot: dict):
    with open(FREEZE_FILE, "w") as f:
        json.dump(snapshot, f, indent=2)


def load_snapshot():
    if not os.path.exists(FREEZE_FILE):
        return None
    with open(FREEZE_FILE, "r") as f:
        return json.load(f)
