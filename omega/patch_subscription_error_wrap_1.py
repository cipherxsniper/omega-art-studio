import re

file_path = "omega_stripe_webhook_revenue_intake_v1.py"

with open(file_path, "r") as f:
    code = f.read()

target = "conn.execute("

if target in code and "[SUBSCRIPTION INSERT ERROR]" not in code:
    code = code.replace(
        target,
        "try:\n        conn.execute("
    )

    code = code.replace(
        "conn.commit()",
        "conn.commit()\n    except Exception as e:\n        print('[SUBSCRIPTION INSERT ERROR]', str(e))"
    )

with open(file_path, "w") as f:
    f.write(code)

print("PATCHED: subscription insert now error-safe")
