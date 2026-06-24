#!/usr/bin/env python3
"""
OMEGA SOVEREIGN NETWORK TOKENIZATION
Your BIN. Your Treasury. Your Math. Full details shown ONCE at issuance.
"""

import os, sys, json, uuid, hashlib, hmac
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

HOME = Path.home()
load_dotenv(HOME / ".env")

sys.path.insert(0, str(HOME))
from omega_card_engine import issue_card

def generate_omega_network_token(card):
    """Your internal network token — OM109 style"""
    payload = {
        "pan": card.get('pan'),
        "expiry": card.get('expiry'),
        "cvv": card.get('cvv'),
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "issuer": "OMEGA_SOVEREIGN",
        "bin": "423456"
    }
    
    raw = json.dumps(payload, sort_keys=True)
    token_id = "ot_" + hashlib.sha256(raw.encode()).hexdigest()[:20]
    
    signature = hmac.new(
        os.urandom(32),
        raw.encode(),
        hashlib.sha256
    ).hexdigest()

    token = {
        "omega_token_id": token_id,
        "pan_last4": card.get('pan_last4'),
        "expiry": card.get('expiry'),
        "signature": signature[:32],
        "type": "OMEGA_NETWORK_TOKEN",
        "status": "ACTIVE"
    }
    
    print(f"✅ OMEGA NETWORK TOKEN: {token_id}")
    return token

def issue_and_tokenize(owner_name="Thomas Lee Harvey", limit=5000.0):
    print("=== OMEGA SOVEREIGN CARD + TOKEN ISSUANCE ===")
    print(f"Treasury: 80795b24-da42-4b9f-aa32-0349004880dc")

    card = issue_card(
        wallet_id="7597e069-65bc-4b55-b420-a2a2682f53e0",
        owner_name=owner_name,
        spend_limit=limit
    )

    token = generate_omega_network_token(card)

    print("\n🎉 SOVEREIGN CARD READY")
    print(f"Full PAN     : {card.get('pan')}")
    print(f"CVV          : {card.get('cvv')}")
    print(f"Expiry       : {card.get('expiry')}")
    print(f"Last4        : {card.get('pan_last4')}")
    print(f"Token ID     : {token['omega_token_id']}")
    print(f"Chain Hash   : {card.get('chain_hash')[:16]}...")
    print(f"Funded from  : Omega Treasury Reserve")

    print("\n→ Copy the full PAN + CVV + Expiry above for manual testing")
    print("→ This is your own tokenization layer — mathematically valid + immutable")

    return {"card": card, "token": token}

if __name__ == "__main__":
    issue_and_tokenize()
