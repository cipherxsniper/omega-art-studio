#!/usr/bin/env python3
import sys

ALLOWED_ENTRY = "omega_unified_system_orchestrator_v1.py"

if __name__ == "__main__":
    if ALLOWED_ENTRY not in sys.argv[0]:
        raise SystemExit(
            "❌ OMEGA LOCKED: must run via unified orchestrator only"
        )
