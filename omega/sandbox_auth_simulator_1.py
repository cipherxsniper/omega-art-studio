#!/usr/bin/env python3

import random
import time

def authorize(card, amount):
    # deterministic-ish risk simulation
    if amount > 1000:
        return {"approved": False, "reason": "LIMIT_EXCEEDED"}

    if random.random() < 0.1:
        return {"approved": False, "reason": "RISK_DECLINE"}

    return {
        "approved": True,
        "auth_code": str(random.randint(100000, 999999))
    }

def capture(auth_result, amount):
    if not auth_result["approved"]:
        return {"captured": False}

    return {
        "captured": True,
        "capture_id": "cap_" + str(random.randint(100000, 999999)),
        "amount": amount
    }

if __name__ == "__main__":
    card = "sandbox"
    auth = authorize(card, 250)
    cap = capture(auth, 250)
    print(auth)
    print(cap)
