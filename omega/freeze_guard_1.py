import inspect
from core.freeze_state import hash_object, load_snapshot, save_snapshot
from core.ledger import LedgerEngine
from core.idempotency import IdempotencyStore


class LogicFreezeViolation(Exception):
    pass


def extract_signature(cls):
    methods = {}
    for name, fn in inspect.getmembers(cls, inspect.isfunction):
        methods[name] = str(inspect.signature(fn))
    return {
        "class": cls.__name__,
        "methods": methods
    }


def build_current_snapshot():
    return {
        "LedgerEngine": extract_signature(LedgerEngine),
        "IdempotencyStore": extract_signature(IdempotencyStore),
    }


def enforce_freeze():
    current = build_current_snapshot()
    current_hash = hash_object(current)

    stored = load_snapshot()

    # FIRST RUN → LOCK STATE
    if stored is None:
        save_snapshot({
            "hash": current_hash,
            "snapshot": current
        })
        print("[FREEZE LOCKED] Initial logic snapshot stored.")
        return

    # COMPARE
    if stored["hash"] != current_hash:
        raise LogicFreezeViolation(
            "YOUR CHANGING LOGIC ERROR: Core system drift detected"
        )
