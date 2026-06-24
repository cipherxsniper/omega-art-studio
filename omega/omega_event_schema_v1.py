import uuid
from datetime import datetime, UTC
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Dict, Any
import json


# =========================================================
# OMEGA CANONICAL EVENT SCHEMA v1
# =========================================================
# THIS IS THE SINGLE SOURCE OF TRUTH
#
# ALL SYSTEMS MUST IMPORT THIS FILE:
#
# - webhook normalization
# - enforcement gate
# - event store
# - replay engine
# - posting engine
# - projection engine
# - telegram control plane
#
# NO DUPLICATED EVENT STRUCTURES ALLOWED.
# =========================================================


# =========================================================
# FROZEN EVENT TYPES
# =========================================================

VALID_EVENT_TYPES = {
    "PAYMENT_CAPTURED",
    "PAYMENT_REVERSED",
    "AUTH_CREATED",
    "AUTH_APPROVED",
    "AUTH_DECLINED",
    "TRANSFER_CREATED",
    "TRANSFER_SETTLED",
    "CARD_CREATED",
    "LEDGER_POSTED",
}


# =========================================================
# FROZEN AGGREGATE TYPES
# =========================================================

VALID_AGGREGATE_TYPES = {
    "PAYMENT",
    "WALLET",
    "CARD",
    "TRANSFER",
    "AUTHORIZATION",
    "TREASURY",
}


# =========================================================
# CANONICAL EVENT MODEL
# =========================================================

@dataclass(frozen=True)
class OmegaEvent:

    event_id: str

    event_type: str

    aggregate_id: str

    aggregate_type: str

    timestamp: str

    merchant_id: str

    wallet_id: str

    amount: str

    currency: str

    payload: Dict[str, Any]

    version: int = 1


# =========================================================
# VALIDATION ENGINE
# =========================================================

def validate_uuid(value: str, field_name: str):

    try:
        UUID(str(value))
    except Exception:
        raise Exception(f"INVALID_UUID_{field_name}")


def validate_event_type(event_type: str):

    if event_type not in VALID_EVENT_TYPES:
        raise Exception(f"INVALID_EVENT_TYPE_{event_type}")


def validate_aggregate_type(aggregate_type: str):

    if aggregate_type not in VALID_AGGREGATE_TYPES:
        raise Exception(f"INVALID_AGGREGATE_TYPE_{aggregate_type}")


def validate_currency(currency: str):

    if len(currency) != 3:
        raise Exception("INVALID_CURRENCY")


def validate_amount(amount: str):

    try:
        Decimal(str(amount))
    except Exception:
        raise Exception("INVALID_AMOUNT")


def validate_required(value, field_name: str):

    if value is None:
        raise Exception(f"MISSING_FIELD_{field_name}")

    if value == "":
        raise Exception(f"MISSING_FIELD_{field_name}")


# =========================================================
# MAIN VALIDATOR
# =========================================================

def validate_event(event: OmegaEvent):

    validate_required(event['event_id'], "event_id")
    validate_required(event['event_type'], "event_type")

    validate_required(event['aggregate_id'], "aggregate_id")
    validate_required(event['aggregate_type'], "aggregate_type")

    validate_required(event['timestamp'], "timestamp")

    validate_required(event['merchant_id'], "merchant_id")

    validate_required(event['wallet_id'], "wallet_id")

    validate_required(event['amount'], "amount")
    validate_required(event['currency'], "currency")

    validate_event_type(event['event_type'])

    validate_aggregate_type(event['aggregate_type'])

    validate_uuid(event['event_id'], "event_id")
    validate_uuid(event['aggregate_id'], "aggregate_id")
    validate_uuid(event['wallet_id'], "wallet_id")

    validate_currency(event['currency'])

    validate_amount(event['amount'])

    return True


# =========================================================
# FACTORY
# =========================================================

def create_event(
    *,
    event_type: str,
    aggregate_id: str,
    aggregate_type: str,
    merchant_id: str,
    wallet_id: str,
    amount: str,
    currency: str,
    payload: Dict[str, Any]
):

    event = OmegaEvent(
        event_id=str(uuid4()),
        event_type=event_type,
        aggregate_id=aggregate_id,
        aggregate_type=aggregate_type,
        timestamp=datetime.utcnow().isoformat(),
        merchant_id=merchant_id,
        wallet_id=wallet_id,
        amount=str(amount),
        currency=currency,
        payload=payload,
    )

    validate_event(event)

    return event


# =========================================================
# SERIALIZATION
# =========================================================

def event_to_dict(event: OmegaEvent):

    return asdict(event)


def event_to_json(event: OmegaEvent):

    return json.dumps(asdict(event))


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    event = create_event(
        event_type="PAYMENT_CAPTURED",
        aggregate_id="00000000-0000-0000-0000-000000000001",
        aggregate_type="PAYMENT",
        merchant_id="omega_merchant",
        wallet_id="00000000-0000-0000-0000-000000000000",
        amount="0.29",
        currency="USD",
        payload={
            "source": "stripe",
            "status": "captured"
        }
    )

    print("✅ OMEGA EVENT SCHEMA v1 FROZEN")
    print(event_to_json(event))



# =========================================================
# EVENT BUILDER
# =========================================================

def build_event(
    event_type,
    aggregate_id,
    aggregate_type,
    merchant_id,
    wallet_id,
    amount,
    currency,
    payload
):

    return {

        "event_id": str(uuid.uuid4()),

        "event_type": event_type,

        "aggregate_id": aggregate_id,
        "aggregate_type": aggregate_type,

        "timestamp": datetime.now(UTC).isoformat(),

        "merchant_id": merchant_id,

        "wallet_id": wallet_id,

        "amount": str(amount),

        "currency": currency,

        "payload": payload,

        "version": 1
    }



# =========================================================
# CANONICAL EVENT TYPES
# =========================================================

EVENT_TYPES = {

    "PAYMENT_CAPTURED": "PAYMENT_CAPTURED",
    "PAYMENT_REVERSED": "PAYMENT_REVERSED",

    "AUTH_CREATED": "AUTH_CREATED",
    "AUTH_APPROVED": "AUTH_APPROVED",
    "AUTH_DECLINED": "AUTH_DECLINED",

    "TRANSFER_CREATED": "TRANSFER_CREATED",
    "TRANSFER_SETTLED": "TRANSFER_SETTLED",

    "CARD_CREATED": "CARD_CREATED",

    "LEDGER_POSTED": "LEDGER_POSTED"
}


# =========================================================
# CANONICAL AGGREGATE TYPES
# =========================================================

AGGREGATE_TYPES = {

    "PAYMENT": "PAYMENT",

    "WALLET": "WALLET",

    "CARD": "CARD",

    "TRANSFER": "TRANSFER",

    "AUTHORIZATION": "AUTHORIZATION",

    "TREASURY": "TREASURY"
}

