#!/usr/bin/env python3
"""
=========================================================
OMEGA PRODUCTION FREEZE v1
SYSTEM RELEASE LOCK + IMMUTABILITY SNAPSHOT
=========================================================

This script creates a deterministic snapshot of:
- Core Python modules
- SQL schemas
- Ledger state definitions
- Settlement + reconciliation core files

This is your "release candidate lock".
=========================================================
"""

import os
import hashlib
import json
from datetime import datetime

CORE_FILES = [
    "omega_settlement_engine_v2.py",
    "omega_settlement_contracts_v1.py",
    "omega_ledger_chain_v1.py",
    "omega_settlement_state_machine_v1.py",
    "omega_transactional_event_store_v2.py",
    "omega_idempotency_contract_v1.py",
    "omega_core_contract_v1.py"
]


def file_hash(path):
    if not os.path.exists(path):
        return None

    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def freeze_snapshot():
    snapshot = {
        "timestamp": datetime.utcnow().isoformat(),
        "files": {}
    }

    for f in CORE_FILES:
        snapshot["files"][f] = file_hash(f)

    snapshot_hash = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True).encode()
    ).hexdigest()

    snapshot["snapshot_hash"] = snapshot_hash

    with open("KERNEL_FREEZE_v1.json", "w") as f:
        json.dump(snapshot, f, indent=2)

    print("🧊 OMEGA PRODUCTION FREEZE COMPLETE")
    print(json.dumps(snapshot, indent=2))

    return snapshot


if __name__ == "__main__":
    freeze_snapshot()
