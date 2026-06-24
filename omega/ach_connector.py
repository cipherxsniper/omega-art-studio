#!/usr/bin/env python3

import uuid
from event_emitter import emit_event

def ingest_ach_event(
    wallet_id,
    amount,
    direction,
    external_reference
):
    payload = {
        "network": "ACH",
        "direction": direction,
        "amount": amount,
        "external_reference": external_reference,
        "status": "SETTLED"
    }

    result = emit_event(
        event_type="ACH_SETTLEMENT_POSTED",
        aggregate_id=wallet_id,
        aggregate_type="WALLET",
        payload=payload,
        idempotency_key=external_reference
    )

    return result

if __name__ == "__main__":

    wallet_id = "70e8cdae-983c-4392-a97a-4ae06217b303"

    result = ingest_ach_event(
        wallet_id=wallet_id,
        amount=1000.00,
        direction="CREDIT",
        external_reference=str(uuid.uuid4())
    )

    print(result)

