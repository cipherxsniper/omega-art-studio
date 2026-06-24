import json, hashlib
from pathlib import Path

BASE = Path.home() / "echoes_of_eternity"
LEDGER = BASE / "om109_ledger.jsonl"

entries = []
with open(LEDGER) as f:
    for line in f:
        line = line.strip()
        if line:
            entries.append(json.loads(line))

by_tid = {}
for e in entries:
    by_tid.setdefault(e["token_id"], []).append(e)

for tid in [95, 96, 97, 98, 99, 100]:
    img_path = BASE / "images" / f"{tid:04d}.png"
    meta_path = BASE / "metadata" / f"{tid:04d}.json"

    disk_hash = None
    if img_path.exists():
        disk_hash = hashlib.sha256(img_path.read_bytes()).hexdigest()

    meta_hash = None
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        for attr in meta.get("attributes", []):
            if attr.get("trait_type") == "SHA256 Fingerprint":
                meta_hash = attr.get("value")

    versions = by_tid[tid]
    print(f"\ntoken {tid}:")
    print(f"  disk image hash : {disk_hash}")
    print(f"  metadata.json   : {meta_hash}")
    for i, v in enumerate(versions):
        match = "  <-- MATCHES DISK" if v["image_sha256"] == disk_hash else ""
        print(f"  occurrence [{i}] : {v['image_sha256']} (minted_at {v['minted_at']}){match}")
