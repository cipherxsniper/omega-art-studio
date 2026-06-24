#!/usr/bin/env python3
path = "/data/data/com.termux/files/home/check_tunnel_stability.sh"
with open(path) as f:
    content = f.read()

old = "test \"$RECENT_COUNT\" -le 15"
new = "test \"$RECENT_COUNT\" -le 25"

if old not in content:
    print("ERROR: threshold line not found")
    print(repr(content))
    raise SystemExit(1)

content = content.replace(old, new, 1)
with open(path, "w") as f:
    f.write(content)
print("Threshold updated 15 → 25")
