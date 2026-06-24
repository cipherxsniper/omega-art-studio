PATH = "/data/data/com.termux/files/home/omega_v10.py"
with open(PATH) as f:
    lines = f.readlines()

# Remove lines 4807-4840 (second copies) — work backwards so indices stay valid
# Find the second occurrence block start
src = "".join(lines)

targets = [
    "def ledger_record_payment(email: str, product_key: str, amount_usd: float):",
    "def ledger_record_churn(email: str, product_key: str, amount_usd: float):",
    "def ledger_record_trial(email: str, product_key: str):",
]

fixed = 0
for target in targets:
    first = src.find(target)
    if first == -1:
        print(f"NOT FOUND: {target[:50]}")
        continue
    second = src.find(target, first + 1)
    if second == -1:
        print(f"NO DUPLICATE: {target[:50]}")
        continue
    # Find end of second function (next def or end of file)
    import re
    rest = src[second:]
    next_def = re.search(r'\ndef [a-zA-Z]', rest[1:])
    if next_def:
        end = second + 1 + next_def.start()
    else:
        end = len(src)
    removed = src[second:end]
    src = src[:second] + src[end:]
    print(f"REMOVED duplicate: {target[:50]}")
    print(f"  Removed {len(removed.splitlines())} lines")
    fixed += 1

with open(PATH, "w") as f:
    f.write(src)
print(f"\nFixed {fixed} duplicates")
