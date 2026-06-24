import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

# Force consistent import root (fixes ModuleNotFoundError: core)
sys.path.append(BASE)
sys.path.append(os.path.join(BASE, "core"))
sys.path.append(os.path.join(BASE, "api"))

print("[BOOTSTRAP] sys.path stabilized")

# Sanity check imports
try:
    import core.ledger
    print("[OK] core.ledger import OK")
except Exception as e:
    print("[FAIL] core.ledger import:", e)

try:
    import core.event_bus
    print("[OK] core.event_bus import OK")
except Exception as e:
    print("[FAIL] core.event_bus import:", e)
