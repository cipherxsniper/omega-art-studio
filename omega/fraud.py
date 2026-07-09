class FraudEngine:

    def score(
        self,
        amount,
        velocity_count,
        merchant_risk
    ):

        risk = 0

        if amount > 10000:
            risk += 40

        if velocity_count > 5:
            risk += 25

        if merchant_risk == "HIGH":
            risk += 35

        return risk
