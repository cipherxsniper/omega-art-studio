
def route_transaction(card_token, amount, merchant_id):
    """
    This is your internal card network router.
    """

    # RULE ENGINE (deterministic routing)
    if amount > 1000:
        route = "HIGH_VALUE_AUTH_PIPE"
    elif merchant_id.startswith("test"):
        route = "SANDBOX_ROUTE"
    else:
        route = "STANDARD_AUTH_PIPE"

    return {
        "route": route,
        "card_token": card_token,
        "amount": amount,
        "approved_for_processing": True
    }
