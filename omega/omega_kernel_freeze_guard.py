import json
import sys

FREEZE_FILE = "KERNEL_FREEZE_v1.json"

def load_freeze():
    with open(FREEZE_FILE, "r") as f:
        return json.load(f)

def assert_kernel_frozen(component_name: str):
    freeze = load_freeze()

    allowed = [
        freeze["posting_engine"],
        freeze["invariant_engine"],
        freeze["replay_engine"]
    ]

    if component_name not in allowed:
        print(f"❄️ KERNEL FROZEN: BLOCKED EXECUTION OF {component_name}")
        sys.exit(1)
