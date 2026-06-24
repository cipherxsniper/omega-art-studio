#!/usr/bin/env python3

import uuid
from event_emitter import emit_event

def ingest_issuer_authorization(
    wallet_id,
    instrument_token,
    amount,
    merchant
):
    payload = {
        "instrument_token": instrument_token,
        "merchant": merchant,
        "amount": amount,
        "currency": "USD",
        "decision": "APPROVED"
    }

    result = emit_event(
        event_type="ISSUER_AUTH_APPROVED",
        aggregate_id=wallet_id,
        aggregate_type="WALLET",
        payload=payload,
        idempotency_key=str(uuid.uuid4())
    )

    return result

if __name__ == "__main__":

    wallet_id = "70e8cdae-983c-4392-a97a-4ae06217b303"

    result = ingest_issuer_authorization(
        wallet_id=wallet_id,
        instrument_token="Ω-INSTR-E68D94B8CBA0625C",
        amount=42.55,
        merchant="OMEGA_STORE"
    )

    print(result)

