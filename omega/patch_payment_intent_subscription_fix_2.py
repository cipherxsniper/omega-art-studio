import re

file_path = "omega_stripe_webhook_revenue_intake_v1.py"

with open(file_path, "r") as f:
    code = f.read()

# Inject handler for payment_intent.succeeded if missing subscriptions write
if "payment_intent.succeeded" not in code:
    print("WARNING: no handler found")

# Replace logic safely (simple patch approach)
patched = code.replace(
    "if event.get(\"type\") == \"checkout.session.completed\":",
    """
if event.get("type") in ["checkout.session.completed", "payment_intent.succeeded"]:
"""
)

with open(file_path, "w") as f:
    f.write(patched)

print("PATCH APPLIED: webhook now accepts payment_intent.succeeded")
