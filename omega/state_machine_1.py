ALLOWED = {
    "REQUESTED": ["AUTHORIZED"],
    "AUTHORIZED": ["HELD"],
    "HELD": ["PENDING_SETTLEMENT"],
    "PENDING_SETTLEMENT": ["SETTLING"],
    "SETTLING": ["SETTLED"],
}

def validate_transition(current, new):
    if current is None:
        return True
    return new in ALLOWED.get(current, [])
