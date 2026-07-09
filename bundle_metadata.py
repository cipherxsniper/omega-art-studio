#!/usr/bin/env python3
"""
One-time bundler: combines all 400 NFT metadata JSON files into a single
all_metadata.json — cuts gallery load from 400 HTTP requests to 1.
Run this once now, and again any time metadata changes (new mints, edits).
"""
import json
from pathlib import Path

HOME = Path("/data/data/com.termux/files/home")

COLLECTIONS = [
    {"slug": "echoes",  "folder": "echoes_of_eternity", "range": (1, 100),    "pad": 4},
    {"slug": "somnium", "folder": "somnium",            "range": (1, 100),    "pad": 4},
    {"slug": "paracosm","folder": "paracosm",           "range": (1001, 1100),"pad": 4},
    {"slug": "monolith","folder": "monolith",           "range": (2001, 2100),"pad": 4},
]

all_tokens = []
missing = []

for coll in COLLECTIONS:
    folder = HOME / coll["folder"] / "metadata"
    start, end = coll["range"]
    for tid in range(start, end + 1):
        idstr = str(tid).zfill(coll["pad"])
        meta_path = folder / f"{idstr}.json"
        if not meta_path.exists():
            missing.append(f"{coll['slug']}/{idstr}")
            continue
        meta = json.loads(meta_path.read_text())
        meta["_slug"] = coll["slug"]
        meta["_folder"] = coll["folder"]
        meta["_pad"] = coll["pad"]
        all_tokens.append(meta)

all_tokens.sort(key=lambda t: (t["_slug"], t.get("token_id", t.get("edition", 0))))

out_path = HOME / "all_metadata.json"
out_path.write_text(json.dumps(all_tokens, indent=2))

print(f"Bundled {len(all_tokens)} tokens into {out_path}")
print(f"Size: {out_path.stat().st_size / 1024:.1f} KB")
if missing:
    print(f"Missing ({len(missing)}): {missing[:10]}{'...' if len(missing) > 10 else ''}")
else:
    print("No missing tokens.")
