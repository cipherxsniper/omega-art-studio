#!/usr/bin/env python3
"""
OMEGA FINAL CARD TEST — Re-issue + immediate test with exact CVV
"""

import sys, json
from pathlib import Path
from dotenv import load_dotenv

HOME = Path.home()
load_dotenv(HOME / ".env")

sys.path.insert(0, str(HOME))
from omega_card_engine import issue_card, authorize_transaction

def test_fresh_card():
    print("=== ISSUING FRESH CARD + IMMEDIATE TEST ===")
    
    card = issue_card(
        wallet_id="7597e069-65bc-4b55-b420-a2a2682f53e0",
        owner_name="Thomas Lee Harvey",
        spend_limit=5000.0
    )

    print(f"Full PAN : {card.get('pan')}")
    print(f"CVV      : {card.get('cvv')}")
    print(f"Token    : {card.get('card_token')}")

    # Use the exact CVV that was just generated
    result = authorize_transaction(
        card_token=card['card_token'],
        amount=1.00,
        merchant="GROK_FINAL_TEST",
        cvv_provided=card['cvv']
    )

    print("\nAuthorization Result:")
    print(json.dumps(result, indent=2, default=str))

    if result.get("approved"):
        print("🎉 APPROVED — CARD WORKS!")
    else:
        print(f"❌ {result.get('reason')}")

if __name__ == "__main__":
    test_fresh_card()
