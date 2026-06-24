class StripeSandboxAdapter:

    def charge(self, amount, currency="usd"):
        # simulate Stripe response
        return {
            "status": "succeeded",
            "amount": amount,
            "currency": currency,
            "provider": "stripe_sandbox"
        }

    def payout(self, amount):
        return {
            "status": "paid",
            "amount": amount
        }
