file = "omega_stripe_webhook_revenue_intake_v1.py"

with open(file, "r") as f:
    lines = f.readlines()

fixed = []

for line in lines:
    # normalize tabs → spaces
    line = line.replace("\t", "    ")

    fixed.append(line)

with open(file, "w") as f:
    f.writelines(fixed)

print("INDENT NORMALIZED (TAB → SPACE SAFE MODE)")
