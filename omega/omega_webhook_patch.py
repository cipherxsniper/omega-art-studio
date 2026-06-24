from stripe_event_bridge import handle_stripe_event

def patched_webhook(stripe, request, STRIPE_WEBHOOK_SECRET, jsonify):
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        return str(e), 400

    result = handle_stripe_event(event)
    print("[OMEGA STRIPE ROUTED]", result)

    return jsonify({"status": "ok", "result": result})
