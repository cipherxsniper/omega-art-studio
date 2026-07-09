#!/usr/bin/env python3

import os
import shutil
from pathlib import Path

SOURCE = str(Path.home() / "Organized_Files")
DEST = str(Path.home() / "Omega-Production" / "omega_bank")

def safe_copy(src, dst):
    os.makedirs(dst, exist_ok=True)

    name = os.path.basename(src)
    base = Path(name).stem
    ext = Path(name).suffix

    candidate = os.path.join(dst, name)

    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(dst, f"{base}_{counter}{ext}")
        counter += 1

    shutil.copy2(src, candidate)
    print(f"COPIED: {src} -> {candidate}")

def main():
    if not os.path.exists(SOURCE):
        print("SOURCE NOT FOUND:", SOURCE)
        return

    if not os.path.exists(DEST):
        os.makedirs(DEST, exist_ok=True)

    files = []

    for root, dirs, filenames in os.walk(SOURCE):
        for f in filenames:
            full = os.path.join(root, f)
            if os.path.isfile(full):
                files.append(full)

    files.sort(key=lambda x: x.lower())

    print(f"FOUND {len(files)} FILES")

    for f in files:
        safe_copy(f, DEST)

    print("DONE RESTORE INTO OMEGA_BANK")

if __name__ == "__main__":
    main()
