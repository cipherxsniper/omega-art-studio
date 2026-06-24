#!/usr/bin/env python3

VALID_EVENTS = {
    "AUTH_CREATED",
    "AUTH_CAPTURED",
    "AUTH_REVERSED",
    "AUTH_EXPIRED",
    "PAYMENT_CAPTURED"
}

REQUIRED_FIELDS = {
    "AUTH_CREATED": ["amount", "wallet_id"],
    "AUTH_CAPTURED": ["amount"],
    "AUTH_REVERSED": ["amount"],
    "AUTH_EXPIRED": ["amount"],
    "PAYMENT_CAPTURED": ["amount", "merchant_id"]
}

class FinancialKernelValidator:

    def validate(self, event_type, event_id, payload):
        if event_type not in VALID_EVENTS:
            return False, f"INVALID_EVENT_TYPE {event_type}"

        required = REQUIRED_FIELDS.get(event_type, [])

        if payload is None:
            return False, "MISSING_PAYLOAD"

        for field in required:
            if field not in payload or payload[field] is None:
                return False, f"MISSING_FIELD {field}"

        return True, "OK"


def validate_event(event_type, event_id, payload):
    return FinancialKernelValidator().validate(event_type, event_id, payload)
