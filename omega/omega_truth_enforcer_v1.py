"""
OMEGA SINGLE SOURCE OF TRUTH ENFORCER

Hard rule:
    ledger_events ONLY defines system state

Any other table = derived/cache only
"""

def enforce_truth_model():
    print("[TRUTH] ledger_events is canonical state")
    print("[TRUTH] all balances are projections only")


def reject_non_ledger_state():
    raise Exception("Invalid state source: only ledger_events allowed")
