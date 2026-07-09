def compute_risk(tx):
    velocity = tx.get("velocity_1m", 0)
    amount = tx.get("amount", 0)
    merchant_score = tx.get("merchant_risk", 0)

    score = (
        velocity * 0.4 +
        (amount / 10000) * 30 +
        merchant_score * 0.3
    )

    return min(100, score)
