#!/usr/bin/env python3

import uuid
from event_emitter import emit_event

def ingest_custody_balance(
    treasury_wallet_id,
    reserve_balance,
    provider
):
    payload = {
        "provider": provider,
        "reserve_balance": reserve_balance,
        "currency": "USD"
    }

    result = emit_event(
        event_type="CUSTODY_RESERVE_SYNC",
        aggregate_id=treasury_wallet_id,
        aggregate_type="TREASURY",
        payload=payload,
        idempotency_key=str(uuid.uuid4())
    )

    return result

if __name__ == "__main__":

    treasury_wallet = "70e8cdae-983c-4392-a97a-4ae06217b303"

    result = ingest_custody_balance(
        treasury_wallet_id=treasury_wallet,
        reserve_balance=1000000000.00,
        provider="OMEGA_CUSTODY"
    )

    print(result)

