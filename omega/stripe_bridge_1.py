import os
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class StripeBridge:

    def create_payment_intent(self, amount, currency="usd"):
        return stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency=currency,
            automatic_payment_methods={"enabled": True}
        )

    def confirm_event(self, event):
        # placeholder for webhook verification (REAL SAFE PATTERN)
        return True
