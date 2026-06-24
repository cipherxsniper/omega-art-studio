#!/usr/bin/env python3

import os
import shutil
from pathlib import Path

BASE = Path.home() / "Omega-Production" / "omega_bank"

MAP = {
    "py": "code",
    "sql": "sql",
    "sh": "scripts",
    "log": "logs",
    "json": "config",
    "txt": "docs",
    "md": "docs",
    "yaml": "config",
    "yml": "config",
}

def category(file: Path):
    ext = file.suffix.lower().replace(".", "")
    return MAP.get(ext, "other")

def move_file(f: Path):
    cat = category(f)
    target_dir = BASE / cat
    target_dir.mkdir(parents=True, exist_ok=True)

    dest = target_dir / f.name

    counter = 1
    while dest.exists():
        dest = target_dir / f"{f.stem}_{counter}{f.suffix}"
        counter += 1

    shutil.move(str(f), str(dest))
    print(f"MOVED {f} -> {dest}")

def main():
    if not BASE.exists():
        print("omega_bank not found")
        return

    files = [p for p in BASE.rglob("*") if p.is_file()]

    files.sort(key=lambda x: x.name.lower())

    print(f"FOUND {len(files)} FILES IN OMEGA_BANK")

    for f in files:
        move_file(f)

    print("CLEANUP COMPLETE")

if __name__ == "__main__":
    main()
