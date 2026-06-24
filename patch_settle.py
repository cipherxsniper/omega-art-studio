import re

with open("/data/data/com.termux/files/home/omega_marketplace.py") as f:
    src = f.read()

with open("/data/data/com.termux/files/home/settle_auction_new.py") as f:
    new_func = f.read().rstrip() + "\n"

pattern = re.compile(r"def settle_auction\(listing_id\):.*?(?=\ndef get_wallet_balance)", re.DOTALL)
if not pattern.search(src):
    raise SystemExit("PATCH FAILED: old settle_auction function not found")

patched = pattern.sub(new_func, src, count=1)

if "from datetime import datetime" not in patched:
    patched = "from datetime import datetime\n" + patched

with open("/data/data/com.termux/files/home/omega_marketplace.py", "w") as f:
    f.write(patched)

print("PATCH APPLIED")
