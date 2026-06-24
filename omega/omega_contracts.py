ALLOWED_EDGES = {
    "telegram": ["orchestrator"],
    "orchestrator": ["ledger", "settlement", "fraud"],
    "ledger": ["settlement", "reconciliation"],
    "settlement": ["ledger"],
    "fraud": ["ledger"],
}

def validate_call(from_system: str, to_system: str):
    if to_system not in ALLOWED_EDGES.get(from_system, []):
        raise RuntimeError(
            f"CONTRACT VIOLATION: {from_system} -> {to_system} not allowed"
        )
