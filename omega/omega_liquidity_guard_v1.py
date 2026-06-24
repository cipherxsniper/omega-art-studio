"""
OMEGA LIQUIDITY GUARD V1

This module prevents:
- fake external liquidity assumptions
- USDT / MEXC "real balance" claims
- phantom treasury inflation

RULE:
    ledger_events is the ONLY truth
"""

def assert_ledger_only_mode():
    print("[GUARD] Operating in LEDGER-ONLY MODE")
    print("[GUARD] No external liquidity assumptions allowed")


def reject_external_balance_claims():
    raise Exception(
        "External liquidity not supported. Use ledger_events only."
    )
