file = "omega_stripe_webhook_revenue_intake_v1.py"

with open(file, "r") as f:
    code = f.read()

# Inject handler call
if "handle_payment_intent_succeeded" not in code:
    print("WARNING: function not imported")

patched = code.replace(
    "if event.get(\"type\") in [\"checkout.session.completed\", \"payment_intent.succeeded\"]:",
    """if event.get("type") in ["checkout.session.completed", "payment_intent.succeeded"]:
        handle_payment_intent_succeeded(event, conn)
"""
)

with open(file, "w") as f:
    f.write(patched)

print("WEBHOOK PATCHED: subscription insert wired")
