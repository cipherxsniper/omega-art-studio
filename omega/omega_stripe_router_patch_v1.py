from omega_subscription_handler_v2 import handle_checkout_session_completed


def route_stripe_event(event, conn):
    event_type = event.get("type")

    if event_type == "checkout.session.completed":
        return handle_checkout_session_completed(event, conn)

    if event_type == "payment_intent.succeeded":
        # fallback path
        return handle_checkout_session_completed(event, conn)

    print("[STRIPE UNHANDLED]", event_type)
    return None
