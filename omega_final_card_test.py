#!/usr/bin/env python3
"""
OMEGA SOVEREIGN CARD TEST — Advanced Production Flow
Full issuance, exact CVV match, persistence fallback, double signature logging.
"""

import sys
import json
import uuid
import hashlib
import hmac
import traceback
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

HOME = Path.home()
load_dotenv(HOME / ".env")

sys.path.insert(0, str(HOME))
from omega_card_engine import issue_card, authorize_transaction, hash_cvv, _card_chain_hash

_LAST_CARD_HASH = "GENESIS"

def advanced_card_test():
    print("=== OMEGA SOVEREIGN CARD TEST — PRODUCTION ===")
    print("Treasury Reserve: 80795b24-da42-4b9f-aa32-0349004880dc")

    # Issue card with your BIN + logic
    try:
        card = issue_card(
            wallet_id="7597e069-65bc-4b55-b420-a2a2682f53e0",
            owner_name="Thomas Lee Harvey",
            spend_limit=5000.0
        )
    except Exception as e:
        print(f"Issuance error: {e}")
        traceback.print_exc()
        return

    print(f"Full PAN : {card.get('pan')}")
    print(f"CVV      : {card.get('cvv')}")
    print(f"Token    : {card.get('card_token')}")

    # Force persistence with exact fields
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="127.0.0.1", port=5432, dbname="omega_bank", 
            user="postgres", connect_timeout=10
        )
        cur = conn.cursor()

        cvv_hash = hash_cvv(card['cvv'])

        cur.execute("""
            INSERT INTO omega_cards (
                card_token, wallet_id, owner_name, pan_encrypted, pan_last4, 
                pan_hash, cvv_hash, expiry_month, expiry_year, status, 
                card_type, spend_limit, spend_used
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, 12, 2030, 'ACTIVE', 
                'VIRTUAL', 5000.00, 0.00
            ) ON CONFLICT (card_token) DO NOTHING
        """, (
            card['card_token'],
            "7597e069-65bc-4b55-b420-a2a2682f53e0",
            "Thomas Lee Harvey",
            card.get('pan_encrypted'),
            card.get('pan_last4'),
            card.get('pan_hash'),
            cvv_hash
        ))

        conn.commit()
        conn.close()
        print("✅ Card persisted with exact CVV hash")
    except Exception as e:
        print(f"Persistence fallback: {e}")

    # Authorize with exact CVV
    result = authorize_transaction(
        card_token=card['card_token'],
        amount=1.00,
        merchant="GROK_FINAL_TEST",
        cvv_provided=card['cvv']
    )

    # Double signature logging
    event_data = {
        "card_token": card['card_token'],
        "amount": 1.00,
        "merchant": "GROK_FINAL_TEST",
        "approved": result.get("approved", False),
        "reason": result.get("reason"),
        "ts": datetime.now(timezone.utc).isoformat()
    }

    global _LAST_CARD_HASH
    chain_hash = _card_chain_hash(event_data, _LAST_CARD_HASH)
    _LAST_CARD_HASH = chain_hash

    om109_fingerprint = hmac.new(
        os.urandom(32),
        json.dumps(event_data, sort_keys=True).encode(),
        hashlib.sha256
    ).hexdigest()[:32]

    print("\nAuthorization Result:")
    print(json.dumps(result, indent=2, default=str))
    print(f"Chain Hash   : {chain_hash[:16]}...")
    print(f"OM109 Print  : {om109_fingerprint[:16]}...")

    if result.get("approved"):
        print("🎉 APPROVED — CARD WORKS IN REAL TRANSACTION!")
    else:
        print(f"❌ {result.get('reason', 'UNKNOWN')}")

if __name__ == "__main__":
    advanced_card_test()
