#!/usr/bin/env python3
"""
Simple clean card test
"""

import sys, json
sys.path.insert(0, "/data/data/com.termux/files/home")
from omega_card_engine import issue_card, authorize_transaction

print("=== ISSUING FRESH CARD ===")
card = issue_card(
    wallet_id="7597e069-65bc-4b55-b420-a2a2682f53e0",
    owner_name="Thomas Lee Harvey",
    spend_limit=5000.0
)

print(f"Full PAN : {card.get('pan')}")
print(f"CVV      : {card.get('cvv')}")
print(f"Token    : {card.get('card_token')}")
print(f"Last4    : {card.get('pan_last4')}")

print("\n--- Now testing authorization with exact CVV ---")
result = authorize_transaction(
    card_token=card'card_token'],
    amount=.00,
    merchant="GROK_TEST",
    cvv_provided=card'cvv']
)

print(json.dumps(result, indent=2, default=str))

if result.get("approved"):
    print("🎉 APPROVED!")
else:
    print(f"❌ {result.get('reason')}")
