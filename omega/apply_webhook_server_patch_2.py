import os

TARGET_FILE = "omega_stripe_webhook_server_v1.py"

PATCH = """
from webhook_route_patch import webhook_route

webhook_route(app, stripe, request, STRIPE_WEBHOOK_SECRET, jsonify)
"""

def apply():
    if not os.path.exists(TARGET_FILE):
        print("[FAIL] webhook server file not found")
        return

    with open(TARGET_FILE, "r") as f:
        lines = f.readlines()

    new_lines = []
    injected = False

    for line in lines:
        # remove old webhook function block if present
        if "@app.route(\"/webhook\"" in line:
            injected = True
            continue
        if injected and "def webhook" in line:
            continue
        if injected and "return" in line:
            continue
        if injected and line.strip() == "":
            continue

        new_lines.append(line)

    # append clean patch at bottom
    new_lines.append("\n" + PATCH + "\n")

    with open(TARGET_FILE, "w") as f:
        f.writelines(new_lines)

    print("[OK] webhook server patched cleanly")

if __name__ == "__main__":
    apply()
