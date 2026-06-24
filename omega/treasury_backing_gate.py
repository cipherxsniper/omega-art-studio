"""
OMEGA TREASURY BACKING GATE
Hard constraint: no issuance without liquidity backing
"""

def enforce_treasury_backing(amount, available_treasury, reserved=0):
    """
    Blocks any credit/authorization that exceeds real liquidity.
    This is the execution firewall.
    """
    effective_liquidity = available_treasury - reserved

    if amount > effective_liquidity:
        raise Exception(
            f"INSUFFICIENT TREASURY BACKING: requested={amount}, available={effective_liquidity}"
        )

    return True


def reserve_liquidity(amount, reserved):
    return reserved + amount


def release_liquidity(amount, reserved):
    return max(0, reserved - amount)
