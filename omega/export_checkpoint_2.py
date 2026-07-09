#!/usr/bin/env python3

import os

CHECKPOINT_DIR = "checkpoints_latest"

os.makedirs(CHECKPOINT_DIR, exist_ok=True)

FILES = [
    f for f in os.listdir(".")
    if f.endswith(".py")
]

for f in FILES:
    with open(f, "r") as src:
        content = src.read()

    out_path = os.path.join(CHECKPOINT_DIR, f)

    with open(out_path, "w") as dst:
        dst.write(content)

    print("[EXPORTED]", f, "->", out_path)

print("\n[CHECKPOINT EXPORT COMPLETE]")
print("DIR:", CHECKPOINT_DIR)
