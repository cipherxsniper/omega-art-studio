import json
from pathlib import Path

BASE = Path.home() / "echoes_of_eternity"
path = BASE / "om109_ledger.jsonl.rebuilt"

entries = [json.loads(l) for l in open(path) if l.strip()]
ids = [e["token_id"] for e in entries]

assert ids == sorted(ids), "NOT sorted"
assert ids == list(range(1, 101)), f"NOT exactly 1-100: missing/extra={set(range(1,101))^set(ids)}"

prev = "OMEGA_NFT_GENESIS"
for i, e in enumerate(entries):
    assert e["prev_chain_hash"] == prev, f"chain break at token {e['token_id']} (index {i})"
    prev = e["chain_hash"]

print(f"OK: {len(entries)} entries, token_ids 1-100, chain verified end to end")
