file = "omega_bank_GITHUB_CHECKPOINT_subscription_fix_v2.py"

with open(file, "r") as f:
    code = f.read()

if "DEBUG SUBSCRIPTION" not in code:
    code = code.replace(
        "obj = event[\"data\"][\"object\"]",
        "obj = event[\"data\"][\"object\"]\n    print('[DEBUG SUBSCRIPTION]', obj)"
    )

with open(file, "w") as f:
    f.write(code)

print("DEBUG INJECTION APPLIED")
