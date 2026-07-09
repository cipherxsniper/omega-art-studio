file = "omega_stripe_webhook_revenue_intake_v1.py"

with open(file, "r") as f:
    lines = f.readlines()

out = []
skip = False

for i, line in enumerate(lines):

    # REMOVE ORPHAN STRIPE ROUTING BLOCK
    if "event_type = event.get" in line:
        break

    # FIX: skip broken duplicate handler call
    if "handle_payment_intent_succeeded(event, conn)" in line:
        continue

    # FIX: remove stray except (we will reconstruct properly later if needed)
    if line.strip().startswith("except Exception"):
        continue

    out.append(line)

with open(file, "w") as f:
    f.writelines(out)

print("WEBHOOK CLEANED: orphan execution + broken blocks removed")
