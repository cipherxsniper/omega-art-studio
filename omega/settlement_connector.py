#!/usr/bin/env python3

import uuid
from event_emitter import emit_event

def finalize_settlement(
    wallet_id,
    amount,
    settlement_reference
):
    payload = {
        "amount": amount,
        "settlement_reference": settlement_reference,
        "status": "FINALIZED"
    }

    result = emit_event(
        event_type="SETTLEMENT_POSTED",
        aggregate_id=wallet_id,
        aggregate_type="WALLET",
        payload=payload,
        idempotency_key=settlement_reference
    )

    return result

if __name__ == "__main__":

    wallet_id = "70e8cdae-983c-4392-a97a-4ae06217b303"

    result = finalize_settlement(
        wallet_id=wallet_id,
        amount=250.00,
        settlement_reference=str(uuid.uuid4())
    )

    print(result)

