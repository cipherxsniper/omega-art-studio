file = "omega_stripe_webhook_revenue_intake_v1.py"

with open(file, "r") as f:
    code = f.read()

# FIX: route events correctly
old = 'if event.get("type") in ["checkout.session.completed", "payment_intent.succeeded"]:'

new = '''event_type = event.get("type")

if event_type == "checkout.session.completed":
    handle_checkout_session_completed(event, conn)

elif event_type == "payment_intent.succeeded":
    handle_payment_intent_succeeded(event, conn)'''

code = code.replace(old, new)

with open(file, "w") as f:
    f.write(code)

print("EVENT ROUTER FIXED: checkout vs payment intent separated")
