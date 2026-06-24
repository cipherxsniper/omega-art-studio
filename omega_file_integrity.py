#!/usr/bin/env python3
"""
omega_file_integrity.py — File location integrity checker for the Oracle.
Catches the file-reorganization blind spot: detects when core files
go missing from their canonical home-root path, even if an identical
copy exists elsewhere in a duplicate folder.
"""
import os
import subprocess

HOME = "/data/data/com.termux/files/home"

EXPECTED_PATHS = {
    "omega_v10.py":             f"{HOME}/omega_v10.py",
    "omega_oracle_v2.py":       f"{HOME}/omega_oracle_v2.py",
    "omega_om109.py":           f"{HOME}/omega_om109.py",
    "omega_consensus.py":       f"{HOME}/omega_consensus.py",
    "omega_sentinel.py":        f"{HOME}/omega_sentinel.py",
    "omega_card_engine.py":     f"{HOME}/omega_card_engine.py",
    "omega_email_finder.py":    f"{HOME}/omega_email_finder.py",
    "omega_guardian.sh":        f"{HOME}/omega_guardian.sh",
    "omega_tunnel_daemon.sh":   f"{HOME}/omega_tunnel_daemon.sh",
    "omega_start.sh":           f"{HOME}/omega_start.sh",
    "omega_storage.py":         f"{HOME}/omega_runtime/omega_storage.py",
    "omega_auth.py":            f"{HOME}/omega_runtime/omega_auth.py",
    "omega_http_server.py":     f"{HOME}/omega_runtime/omega_http_server.py",
    "omega_tls_server.py":      f"{HOME}/omega_runtime/omega_tls_server.py",
    "omega_vps_engine.py":      f"{HOME}/omega_runtime/omega_vps_engine.py",
    "omega_ddns.py":            f"{HOME}/omega_runtime/omega_ddns.py",
    "omega_companion_server.py": f"{HOME}/omega_companion_server.py",
    "vps_registry.json":        f"{HOME}/omega_runtime/vps_registry.json",
    "om109_chain.json":         f"{HOME}/omega_runtime/state/om109_chain.json",
    "omega_spawn_engine.py":    f"{HOME}/omega_spawn_engine.py",
    "omega_dashboard_bridge.py": f"{HOME}/omega_dashboard_bridge.py",
    "omega_provenance_api.py":  f"{HOME}/omega_provenance_api.py",
}


def check_file_integrity():
    """
    Returns (missing, wrong_location) where:
      missing         -> list of filenames not found at their expected path
      wrong_location  -> list of human-readable strings naming where
                         a missing file was actually found instead
    """
    missing = []
    wrong_location = []

    for name, expected_path in EXPECTED_PATHS.items():
        if not os.path.exists(expected_path):
            missing.append(name)
            try:
                result = subprocess.run(
                    ["find", HOME, "-maxdepth", "4", "-iname", name],
                    capture_output=True, text=True, timeout=10
                )
                found_paths = [
                    p for p in result.stdout.strip().split("\n") if p
                ]
                if found_paths:
                    wrong_location.append(
                        f"{name} found at {found_paths[0]} instead"
                    )
                else:
                    wrong_location.append(
                        f"{name} not found anywhere under {HOME}"
                    )
            except subprocess.TimeoutExpired:
                wrong_location.append(f"{name} search timed out")

    return missing, wrong_location


def score_file_integrity():
    """
    Returns (score, issues) for Oracle integration.
    100 if every expected file is in place.
    Deducts 100/N points per missing file, N = total tracked files.
    """
    missing, wrong_location = check_file_integrity()
    total_tracked = len(EXPECTED_PATHS)

    if not missing:
        return 100, []

    penalty_per_file = 100 / total_tracked
    score = max(0, 100 - int(len(missing) * penalty_per_file))

    issues = []
    for name, location_hint in zip(missing, wrong_location):
        issues.append(f"MISSING: {name} — {location_hint}")

    return score, issues


if __name__ == "__main__":
    score, issues = score_file_integrity()
    print(f"omega_file_integrity: {score}/100")
    if issues:
        print(f"\nIssues ({len(issues)}):")
        for issue in issues:
            print(f"  • {issue}")
    else:
        print("All tracked files present at canonical paths.")
