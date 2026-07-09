#!/usr/bin/env python3

import os
import shutil
from pathlib import Path

SOURCE = str(Path.home() / "Organized_Files")
DEST = str(Path.home() / "omega")

def safe_name(dest_dir, filename):
    base = Path(filename).stem
    ext = Path(filename).suffix

    candidate = os.path.join(dest_dir, filename)
    if not os.path.exists(candidate):
        return candidate

    i = 1
    while True:
        new_name = f"{base}_{i}{ext}"
        candidate = os.path.join(dest_dir, new_name)
        if not os.path.exists(candidate):
            return candidate
        i += 1

def main():
    os.makedirs(DEST, exist_ok=True)

    count = 0

    for root, _, files in os.walk(SOURCE):
        for f in files:
            if not f.endswith(".py"):
                continue

            src = os.path.join(root, f)
            dst = safe_name(DEST, f)

            try:
                shutil.move(src, dst)
                print(f"MOVED: {src} -> {dst}")
                count += 1
            except Exception as e:
                print(f"FAILED: {src} -> {e}")

    print("\nDONE")
    print("TOTAL MOVED:", count)
    print("DEST:", DEST)

if __name__ == "__main__":
    main()
