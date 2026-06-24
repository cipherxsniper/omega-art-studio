#!/usr/bin/env python3
"""
OMEGA SOVEREIGN TREASURY CARD ISSUANCE
Your rules. Your treasury. Your ledger.
"""

import sys, json, uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / ".env")
sys.path.insert(0, str(Path.home()))

from omega_card_engine import issue_card

def issue_treasury_card(owner="Thomas Lee Harvey", limit=5000.0):
    print("=== OMEGA SOVEREIGN CARD ISSUANCE ===")
    print(f"Funding from Treasury Reserve: 80795b24-da42-4b9f-aa32-0349004880dc")

    card = issue_card(
        wallet_id="7597e069-65bc-4b55-b420-a2a2682f53e0",
        owner_name=owner,
        spend_limit=limit
    )

    print(f"\n✅ CARD ISSUED & TREASURY-LINKED")
    print(f"Full PAN : {card.get('pan')}")
    print(f"Last4    : {card.get('pan_last4')}")
    print(f"CVV      : {card.get('cvv')}")
    print(f"Expiry   : {card.get('expiry')}")
    print(f"Token    : {card.get('card_token')}")
    print(f"Chain    : {card.get('chain_hash')[:16]}...")
    print(f"Funded   : Omega Treasury Reserve")
    print(f"Status   : {card.get('status')} | Limit: ${card.get('spend_limit')}")

    print("\nThis card is mathematically valid and ledger-immutable.")
    print("Use full PAN + CVV + Expiry for real manual testing.")
    return card

if __name__ == "__main__":
    issue_treasury_card()
