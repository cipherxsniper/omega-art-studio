#!/usr/bin/env python3

import random

# Luhn checksum generator (valid structure, NOT network-issued)
def luhn_checksum(base):
    digits = [int(d) for d in base]
    checksum = 0
    parity = len(digits) % 2

    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d

    return (10 - (checksum % 10)) % 10

def generate_sandbox_card():
    # "4" mimics Visa BIN pattern BUT IS NOT A VISA CARD
    base = [4] + [random.randint(0, 9) for _ in range(14)]
    check = luhn_checksum(base)
    return "".join(map(str, base)) + str(check)

def issue_card(wallet_id):
    return {
        "card_id": "card_" + str(random.randint(100000, 999999)),
        "pan": generate_sandbox_card(),
        "wallet_id": wallet_id,
        "status": "ACTIVE",
        "network": "OMEGA_SANDBOX_ISSUER"
    }

if __name__ == "__main__":
    print(issue_card("test-wallet"))
