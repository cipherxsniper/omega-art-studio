#!/usr/bin/env python3
"""
OMEGA FROZEN FEATURE REGISTRY
Locks in verified runtime behavior, not just file-compiles-cleanly.
Once a feature is confirmed working, the Oracle checks it forever.
A frozen feature can never silently regress without being caught.
"""
import json, subprocess, time
from pathlib import Path
from datetime import datetime

HOME = Path("/data/data/com.termux/files/home")
REGISTRY = HOME / "omega_frozen_registry.json"

def load_registry():
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text())
    return {"frozen": {}}

def save_registry(data):
    REGISTRY.write_text(json.dumps(data, indent=2))

def freeze(name: str, check_type: str, target: str, expected_contains: str = None):
    """
    Freeze a feature's verified behavior.
    check_type: 'http' (curl a URL, expect 200) or 'cmd' (run shell cmd, check output)
    """
    reg = load_registry()
    reg["frozen"][name] = {
        "check_type": check_type,
        "target": target,
        "expected_contains": expected_contains,
        "frozen_at": datetime.now().isoformat(),
        "last_verified": None,
        "status": "FROZEN"
    }
    save_registry(reg)
    print(f"FROZEN: {name} ({check_type}: {target})")

def verify_all():
    """Run every frozen check. Return list of regressions."""
    reg = load_registry()
    regressions = []
    for name, spec in reg["frozen"].items():
        ok = False
        detail = ""
        try:
            if spec["check_type"] == "http":
                result = subprocess.run(
                    ["curl", "-s", "--max-time", "3", spec["target"]],
                    capture_output=True, text=True, timeout=15
                )
                output = result.stdout
                if spec.get("expected_contains"):
                    ok = spec["expected_contains"] in output
                else:
                    ok = len(output) > 0
                detail = output[:100]
            elif spec["check_type"] == "cmd":
                result = subprocess.run(
                    spec["target"], shell=True,
                    capture_output=True, text=True, timeout=15
                )
                output = result.stdout
                if spec.get("expected_contains"):
                    ok = spec["expected_contains"] in output
                else:
                    ok = result.returncode == 0
                detail = output[:100]
        except Exception as e:
            ok = False
            detail = str(e)[:100]

        reg["frozen"][name]["last_verified"] = datetime.now().isoformat()
        reg["frozen"][name]["status"] = "VERIFIED" if ok else "REGRESSED"

        if not ok:
            regressions.append((name, detail))

    save_registry(reg)
    return regressions

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        regs = verify_all()
        if regs:
            print(f"REGRESSIONS DETECTED: {len(regs)}")
            for name, detail in regs:
                print(f"  - {name}: {detail}")
            sys.exit(1)
        else:
            print("All frozen features verified OK")
    else:
        print("Usage: omega_frozen_registry.py verify")
