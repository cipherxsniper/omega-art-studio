from core.event_bus import EventBus
from models.subscriptions import create_subscription

def install_stripe_dispatch():
    bus = EventBus()

    def handler(event):
        if event.get("type") == "payment_intent.succeeded":
            create_subscription(event)

    bus.subscribe("stripe", handler)

    print("[OK] Stripe dispatch handler installed")

if __name__ == "__main__":
    install_stripe_dispatch()
