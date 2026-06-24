from datetime import datetime, timezone
from omega_snapshot_contract_patch_v1 import normalize_snapshot

def build_consensus_snapshot(events, balances):
    normalized_balances = balances

    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_count": len(events),
        "ledger_event_count": len(events),
        "balances": normalized_balances,
        "system_state": "CONSENSUS_VALID"
    }

    snapshot = normalize_snapshot(snapshot)

    return snapshot


def run():
    print("🧠 CONSENSUS ENGINE RUNNING")
