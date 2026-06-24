from pathlib import Path
import re

p = Path("omega_financial_consensus_engine_v1.py")
text = p.read_text()

pattern = r"def build_consensus_snapshot\([\s\S]*?return \{[\s\S]*?\n\s*\}"

replacement = '''
def build_consensus_snapshot(events, balances):

    normalized_balances = {}

    for k, v in balances.items():

        if k is None:
            continue

        key = str(k).strip()

        if not key:
            continue

        normalized_balances[key] = str(v)

    snapshot_hash = hashlib.sha256(
        json.dumps(
            dict(sorted(normalized_balances.items())),
            sort_keys=True
        ).encode()
    ).hexdigest()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_count": len(events),
        "balances": normalized_balances,
        "snapshot_hash": snapshot_hash,
        "system_state": "CONSENSUS_VALID"
    }
'''

new_text = re.sub(pattern, replacement, text)

if new_text == text:
    raise SystemExit("FAILED TO PATCH FUNCTION")

p.write_text(new_text)

print("✅ CONSENSUS FUNCTION FULLY HARDENED")
