ALLOWED_EVENT_TYPES = {
    "PAYMENT_CAPTURED",
    "PAYMENT_SETTLED",
    "PAYMENT_RESERVED"
}

def is_financial_event(event_type):
    return event_type in ALLOWED_EVENT_TYPES
