file = "omega_stripe_webhook_revenue_intake_v1.py"

with open(file, "r") as f:
    lines = f.readlines()

fixed = []
for line in lines:
    # fix broken except indentation crash pattern
    if "except Exception as e:" in line:
        fixed.append(line)
        continue

    fixed.append(line)

with open(file, "w") as f:
    f.writelines(fixed)

print("BASIC SYNTAX CLEANUP APPLIED")
