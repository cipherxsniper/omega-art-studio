#!/usr/bin/env python3
import json, hashlib
from pathlib import Path

BASE = Path.home() / "echoes_of_eternity"
LEDGER = BASE / "om109_ledger.jsonl"
GENESIS = "OMEGA_NFT_GENESIS"

entries = []
with open(LEDGER) as f:
    for line in f:
        line = line.strip()
        if line:
            entries.append(json.loads(line))
print(f"Read {len(entries)} lines")

by_tid = {}
for e in entries:
    tid = e["token_id"]
    by_tid.setdefault(tid, []).append(e)

print(f"Unique token_ids: {len(by_tid)}")

kept = {}
for tid, versions in by_tid.items():
    if len(versions) == 1:
        kept[tid] = versions[0]
    else:
        latest = max(versions, key=lambda e: e["minted_at"])
        kept[tid] = latest
        print(f"  token {tid}: {len(versions)} versions, keeping latest (minted_at {latest['minted_at']}, image {latest['image_sha256'][:16]}...)")

final = {tid: e for tid, e in kept.items() if 1 <= tid <= 100}
excluded = sorted(set(kept.keys()) - set(final.keys()))
print(f"Excluding token_ids: {excluded}")
print(f"Final count: {len(final)}")

if len(final) != 100:
    print(f"WARNING: expected 100, got {len(final)} — STOPPING, review manually")
    raise SystemExit(1)

prev_hash = GENESIS
rebuilt = []
for tid in sorted(final.keys()):
    e = dict(final[tid])
    e.pop("chain_hash", None)
    e["prev_chain_hash"] = prev_hash
    chain_hash = hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest()
    e["chain_hash"] = chain_hash
    rebuilt.append(e)
    prev_hash = chain_hash

out_path = BASE / "om109_ledger.jsonl.rebuilt"
with open(out_path, "w") as f:
    for e in rebuilt:
        f.write(json.dumps(e) + "\n")

print(f"Wrote {len(rebuilt)} entries to {out_path}")
print("Review, then: mv om109_ledger.jsonl.rebuilt om109_ledger.jsonl")
