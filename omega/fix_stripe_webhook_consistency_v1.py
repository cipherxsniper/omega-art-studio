import os

FILES = [
    "omega_stripe_webhook_server_v1.py",
    "api/webhook_server.py",
    "omega_stripe_webhook_revenue_intake_v1.py"
]

OLD_1 = "STRIPE_WEBHOOK_SECRET_2"
OLD_2 = "STRIPE_WEBHOOK_SECRET_3"

NEW = "STRIPE_WEBHOOK_SECRET"

def fix_file(path):
    with open(path, "r") as f:
        data = f.read()

    data = data.replace(OLD_1, NEW)
    data = data.replace(OLD_2, NEW)

    with open(path, "w") as f:
        f.write(data)

    print(f"FIXED: {path}")

for f in FILES:
    if os.path.exists(f):
        fix_file(f)

print("DONE: Stripe webhook secrets unified")
