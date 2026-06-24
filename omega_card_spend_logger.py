#!/usr/bin/env python3
"""
OMEGA CARD TESTER — Forces latest card + logs double signed attempt
"""

import os, sys, json, uuid, hashlib, hmac
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

HOME = Path.home()
load_dotenv(HOME / ".env")

sys.path.insert(0, str(HOME))
from omega_card_engine import authorize_transaction, _card_chain_hash

_LAST_CARD_HASH = "GENESIS"

def test_latest_card():
    # Use the MOST RECENT token you just issued
    card_token = "oc_b0626630b98f1d3ea029644f"   # ← update if you issued newer
    cvv = "653"                                   # ← update if newer

    print(f"Testing latest card ending {card_token[-4:]}")
    result = authorize_transaction(
        card_token=card_token,
        amount=1.00,
        merchant="GROK_REAL_TEST",
        cvv_provided=cvv
    )

    event_data = {
        "card_token": card_token,
        "amount": 1.00,
        "merchant": "GROK_REAL_TEST",
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

    print(json.dumps(result, indent=2, default=str))
    print(f"Chain Hash   : {chain_hash[:16]}...")
    print(f"OM109 Print  : {om109_fingerprint[:16]}...")
    print("✅ Double Signed — Attempt Logged")

    if result.get("approved"):
        print("🎉 SUCCESS — CARD WORKS")
    else:
        print("❌ Still CARD_NOT_FOUND — DB persistence issue")

if __name__ == "__main__":
    test_latest_card()
