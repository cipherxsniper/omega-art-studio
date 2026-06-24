import os
import stripe
from fastapi import Request

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

def attach_webhook(app):

    @app.post("/webhook")
    async def webhook(request: Request):
        payload = await request.body()
        sig = request.headers.get("stripe-signature")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig, STRIPE_WEBHOOK_SECRET
            )
        except Exception as e:
            print("[WEBHOOK ERROR]", str(e))
            return {"error": str(e)}

        event_type = event.get("type")
        print("[OMEGA WEBHOOK EVENT]", event_type)

        # minimal routing (safe baseline)
        if event_type == "payment_intent.succeeded":
            print("[LEDGER HOOK] payment success")

        if event_type == "checkout.session.completed":
            print("[SUBSCRIPTION HOOK] checkout completed")

        if event_type == "invoice.paid":
            print("[REVENUE HOOK] invoice paid")

        return {"status": "ok", "type": event_type}
