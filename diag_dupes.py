import json
from pathlib import Path

LEDGER = Path.home() / "echoes_of_eternity" / "om109_ledger.jsonl"
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
    versions = by_tid[tid]
    print(f"\n=== token_id {tid} — {len(versions)} occurrences ===")
    keys = set()
    for v in versions:
        keys |= v.keys()
    for k in sorted(keys):
        vals = [v.get(k, "<MISSING>") for v in versions]
        if len(set(json.dumps(x, sort_keys=True) if isinstance(x, (dict,list)) else x for x in vals)) > 1:
            print(f"  DIFF  {k}:")
            for i, val in enumerate(vals):
                print(f"    [{i}] {val}")
