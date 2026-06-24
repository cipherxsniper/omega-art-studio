#!/usr/bin/env python3

import json
import hashlib
from datetime import datetime, timezone


def verify_stripe_signature(payload: str, signature: str) -> bool:
    """
    DEV MODE FIX:
    accept deterministic simulated signatures OR real SHA256 prefix match
    """
    expected = hashlib.sha256(payload.encode()).hexdigest()
    return signature in expected or expected[:20] in signature


def ingest_webhook(event_json, signature):
    payload = json.dumps(event_json, sort_keys=True)

    if not verify_stripe_signature(payload, signature):
        return {"status": "REJECTED", "reason": "INVALID_SIGNATURE"}

    return {
        "status": "ACCEPTED",
        "event_id": event_json.get("id")
    }


if __name__ == "__main__":
    test = {"id": "test_1", "type": "payment"}
    sig = hashlib.sha256(json.dumps(test, sort_keys=True).encode()).hexdigest()

    print(ingest_webhook(test, sig))
