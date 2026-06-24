#!/usr/bin/env python3

import uuid
import random
from datetime import datetime

def generate_card(wallet_id):
    return {
        "card_id": str(uuid.uuid4()),
        "wallet_id": wallet_id,
        "card_number": "4111" + "".join([str(random.randint(0,9)) for _ in range(12)]),
        "expiry": "12/30",
        "cvv": str(random.randint(100,999)),
        "status": "ACTIVE",
        "created_at": str(datetime.utcnow())
    }

def authorize(card, amount, merchant):
    return {
        "auth_id": str(uuid.uuid4()),
        "wallet_id": card["wallet_id"],
        "merchant": merchant,
        "amount": amount,
        "status": "AUTHORIZED",
        "timestamp": str(datetime.utcnow())
    }

if __name__ == "__main__":
    wallet = "fe881e17-8b24-42f4-ba4f-c1ce38770b51"

    card = generate_card(wallet)

    print("\n=== GENERATED TEST CARD ===")
    print(card)

    auth = authorize(card, 125.55, "OMEGA_TEST_MERCHANT")

    print("\n=== AUTHORIZATION RESULT ===")
    print(auth)
