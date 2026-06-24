import random
import hashlib
import time


def generate_card_number():
    """
    Sandbox-only card generator.
    NOT real payment network compatible.
    Deterministic format: 16-digit Luhn-like structure (simplified)
    """

    base = "4"  # Visa-style prefix for simulation only (NOT real network use)

    body = "".join(str(random.randint(0, 9)) for _ in range(14))

    raw = base + body

    # lightweight deterministic checksum (NOT real Luhn, but stable for testing)
    checksum = int(hashlib.sha256(raw.encode()).hexdigest(), 16) % 10

    return raw + str(checksum)


def issue_virtual_card(wallet_id, limit):
    return {
        "card_number": generate_card_number(),
        "wallet_id": wallet_id,
        "spending_limit": float(limit),
        "status": "ACTIVE",
        "created_at": time.time()
    }
