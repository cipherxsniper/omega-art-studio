#!/usr/bin/env python3

import json
import shutil
from pathlib import Path

MAP_FILE = Path.home() / "omega_original_path_map.json"
DEST_ROOT = Path.home()

def safe_copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)

    target = dst
    i = 1

    while target.exists():
        target = dst.with_name(f"{dst.stem}_{i}{dst.suffix}")
        i += 1

    shutil.copy2(src, target)
    print(f"RESTORED: {src} -> {target}")

def main():
    with open(MAP_FILE, "r") as f:
        mapping = json.load(f)

    for src, rel in mapping.items():
        src_path = Path(src)
        if not src_path.exists():
            continue

        dest_path = DEST_ROOT / rel
        safe_copy(src_path, dest_path)

    print("FULL ORIGINAL STRUCTURE RESTORED")

if __name__ == "__main__":
    main()
