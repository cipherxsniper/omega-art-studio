def route_stripe_event(event, conn):
    event_type = event.get("type")

    if event_type == "checkout.session.completed":
        return handle_checkout_session_completed(event, conn)

    if event_type == "payment_intent.succeeded":
        return handle_payment_intent_succeeded(event, conn)

    if event_type == "invoice.paid":
        return handle_invoice_paid(event, conn)

    print("[STRIPE SKIP] unhandled event:", event_type)
    return None
