#!/usr/bin/env python3

import os
from pathlib import Path
import json

SRC = Path.home() / "Organized_Files"
OUT = Path.home() / "omega_original_path_map.json"

def infer_original_path(file_path: str):
    p = file_path.lower()
    name = os.path.basename(file_path)

    # CORE OMEGA SYSTEMS (your real projects)
    if "omega-fintech" in p or "finance" in p:
        return f"omega-fintech/{name}"

    if "omega_runtime" in p or "runtime" in p:
        return f"omega_runtime/{name}"

    if "omega_production" in p or "omega-production" in p:
        return f"Omega-Production/{name}"

    if name.startswith("omega_"):
        return f"Omega-Production/modules/{name}"

    if p.endswith(".sql"):
        return f"Omega-Production/db/{name}"

    if p.endswith(".sh"):
        return f"Omega-Production/scripts/{name}"

    if p.endswith(".py"):
        return f"Omega-Production/core/{name}"

    return f"misc/{name}"

def main():
    mapping = {}

    files = [str(p) for p in SRC.rglob("*") if p.is_file()]

    for f in files:
        mapping[f] = infer_original_path(f)

    with open(OUT, "w") as fp:
        json.dump(mapping, fp, indent=2)

    print(f"ORIGIN MAP GENERATED: {OUT}")
    print(f"FILES ANALYZED: {len(files)}")

if __name__ == "__main__":
    main()
