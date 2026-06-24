#!/usr/bin/env python3

import os
import shutil
from pathlib import Path

SOURCE = Path.home() / "Organized_Files"
DEST = Path.home() / "Omega-RESTORED"

def infer_root(path: Path):
    p = str(path).lower()

    if "omega" in p:
        return "Omega-Production"
    if "sql" in p:
        return "databases"
    if "script" in p or p.endswith(".sh"):
        return "scripts"
    if "code" in p or p.endswith(".py"):
        return "code"
    if "log" in p:
        return "logs"
    if "android" in p or "apk" in p:
        return "android"
    return "misc"

def safe_copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)

    target = dst
    counter = 1

    while target.exists():
        target = dst.with_name(f"{dst.stem}_{counter}{dst.suffix}")
        counter += 1

    shutil.copy2(src, target)
    print(f"RESTORED: {src} -> {target}")

def main():
    if not SOURCE.exists():
        print("SOURCE NOT FOUND")
        return

    files = [p for p in SOURCE.rglob("*") if p.is_file()]
    files.sort(key=lambda x: x.name.lower())

    print(f"FOUND {len(files)} FILES")

    for f in files:
        root = infer_root(f)
        relative = f.name

        target_dir = DEST / root
        target_file = target_dir / relative

        safe_copy(f, target_file)

    print("RESTORE COMPLETE -> Omega-RESTORED")

if __name__ == "__main__":
    main()
