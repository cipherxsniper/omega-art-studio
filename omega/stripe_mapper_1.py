class StripeMapper:

    def to_omega_event(self, stripe_event):

        event_type = stripe_event["type"]
        obj = stripe_event["data"]["object"]

        if event_type == "payment_intent.succeeded":

            return {
                "type": "STRIPE_FUNDS_RECEIVED",
                "amount": obj["amount_received"] / 100,
                "source": "stripe",
                "stripe_id": stripe_event["id"]
            }

        if event_type == "payout.paid":

            return {
                "type": "STRIPE_PAYOUT_COMPLETED",
                "amount": obj["amount"] / 100,
                "source": "stripe",
                "stripe_id": stripe_event["id"]
            }

        return None
