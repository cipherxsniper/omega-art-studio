path = "/data/data/com.termux/files/home/omega_marketplace.py"
with open(path) as f:
    src = f.read()

old = '''            success, msg = place_bid(1, wallet2, 600.0)'''
new = '''            import re
            m = re.search(r"auction #(\\d+)", msg)
            new_listing_id = int(m.group(1)) if m else 1
            success, msg = place_bid(new_listing_id, wallet2, 600.0)'''

if old not in src:
    raise SystemExit("PATCH FAILED: target line not found")

src = src.replace(old, new, 1)
with open(path, "w") as f:
    f.write(src)
print("PATCH APPLIED")
