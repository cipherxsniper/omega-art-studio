from pathlib import Path

files = [
    "omega_stripe_webhook_revenue_intake_v1.py",
    "omega_stripe_webhook_server_v1.py",
    "api/webhook_server.py"
]

for f in files:
    p = Path(f)
    if not p.exists():
        continue

    text = p.read_text()

    # FIX 1: remove JSON parsing usage
    text = text.replace("request.get_json()", "request.data")

    # FIX 2: ensure raw payload pattern exists
    if "request.data" not in text:
        text = text.replace(
            "request",
            "request.data if hasattr(request, 'data') else request"
        )

    p.write_text(text)
    print("PATCHED:", f)

print("DONE: RAW STRIPE BODY FIX APPLIED")
