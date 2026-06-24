#!/usr/bin/env python3
"""
OMEGA STORAGE WATCH v1.0
Storage monitoring module for Oracle v2 grading system.
Monitors: disk usage, DB size, log growth, inode health.
Weight: 5% (suggested) in Oracle scoring.
Author: Thomas Lee Harvey / Omega AI
"""

import os
import sys
import json
import hashlib
import sqlite3
import subprocess
import time
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────
HOME = os.path.expanduser("~")
DB_PATH = os.path.join(HOME, "omega_runtime", "db", "omega.db")
LOG_DIR = os.path.join(HOME, "omega_runtime", "logs")
ORACLE_SNAPSHOT = os.path.join(HOME, "omega_sentinel_snapshot.json")
STORAGE_STATE = os.path.join(HOME, "omega_storage_state.json")

# Thresholds (percentages)
DISK_WARN = 85      # Yellow alert
DISK_CRIT = 95      # Red alert
DB_WARN_GB = 2.0    # SQLite DB warning
DB_CRIT_GB = 4.0    # SQLite DB critical
LOG_WARN_GB = 1.0   # Log dir warning
LOG_CRIT_GB = 2.0   # Log dir critical
INODE_WARN = 90     # Inode usage warning
INODE_CRIT = 98     # Inode usage critical

# ─── HELPERS ──────────────────────────────────────────────

def run_shell(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def get_disk_usage(path="/data"):
    """Get disk usage for a path using statvfs (no subprocess)."""
    try:
        stat = os.statvfs(path)
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bfree * stat.f_frsize
        used = total - free
        pct = round((used / total) * 100, 2) if total > 0 else 0
        return {
            "path": path,
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "used_pct": pct,
            "total_human": human_bytes(total),
            "used_human": human_bytes(used),
            "free_human": human_bytes(free)
        }
    except Exception as e:
        return {"path": path, "error": str(e), "used_pct": 100}

def get_inode_usage(path="/data"):
    """Get inode usage for a path."""
    try:
        stat = os.statvfs(path)
        total = stat.f_files
        free = stat.f_ffree
        used = total - free
        pct = round((used / total) * 100, 2) if total > 0 else 0
        return {
            "total": total,
            "used": used,
            "free": free,
            "used_pct": pct
        }
    except Exception as e:
        return {"error": str(e), "used_pct": 100}

def human_bytes(b):
    """Convert bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024.0:
            return f"{b:.2f} {unit}"
        b /= 1024.0
    return f"{b:.2f} PB"

def get_file_size(path):
    """Get size of a file or directory (recursive)."""
    try:
        if os.path.isfile(path):
            return os.path.getsize(path)
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    total += os.path.getsize(fp)
        return total
    except Exception as e:
        return 0

def get_db_stats():
    """Get SQLite database stats."""
    stats = {"exists": False, "size_bytes": 0, "size_human": "0 B", "tables": 0, "entries": 0}
    if not os.path.exists(DB_PATH):
        return stats
    stats["exists"] = True
    stats["size_bytes"] = os.path.getsize(DB_PATH)
    stats["size_human"] = human_bytes(stats["size_bytes"])
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        stats["tables"] = len(tables)
        total_entries = 0
        for (table,) in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                total_entries += cursor.fetchone()[0]
            except:
                pass
        stats["entries"] = total_entries
        conn.close()
    except Exception as e:
        stats["error"] = str(e)
    return stats

def get_log_stats():
    """Get log directory stats."""
    stats = {"exists": False, "size_bytes": 0, "size_human": "0 B", "files": 0, "largest_file": "N/A"}
    if not os.path.exists(LOG_DIR):
        return stats
    stats["exists"] = True
    stats["size_bytes"] = get_file_size(LOG_DIR)
    stats["size_human"] = human_bytes(stats["size_bytes"])
    try:
        files = [f for f in os.listdir(LOG_DIR) if os.path.isfile(os.path.join(LOG_DIR, f))]
        stats["files"] = len(files)
        if files:
            largest = max(files, key=lambda f: os.path.getsize(os.path.join(LOG_DIR, f)))
            stats["largest_file"] = f"{largest} ({human_bytes(os.path.getsize(os.path.join(LOG_DIR, largest)))})"
    except Exception as e:
        stats["error"] = str(e)
    return stats

def get_termux_storage():
    """Get Termux-specific storage info."""
    storage = {}
    # Internal storage
    storage["internal"] = get_disk_usage("/data")
    # Check if external storage mounted
    ext_paths = ["/sdcard", "/storage/emulated/0", "/storage/self/primary"]
    for p in ext_paths:
        if os.path.ismount(p) or os.path.exists(p):
            storage["external"] = get_disk_usage(p)
            break
    # Termux home
    storage["termux_home"] = get_disk_usage(HOME)
    return storage

# ─── SCORING ENGINE ───────────────────────────────────────

def calculate_score(disk, inode, db, logs):
    """
    Oracle-style scoring: 0-100 based on thresholds.
    Each component contributes to final score.
    """
    score = 100
    issues = []
    critical = 0
    warnings = 0

    # Disk usage scoring
    disk_pct = disk.get("used_pct", 0)
    if disk_pct >= DISK_CRIT:
        score -= 40
        critical += 1
        issues.append(f"DISK CRITICAL: {disk_pct}% used ({disk.get('used_human', '?')})")
    elif disk_pct >= DISK_WARN:
        score -= 20
        warnings += 1
        issues.append(f"DISK WARNING: {disk_pct}% used ({disk.get('used_human', '?')})")

    # Inode scoring
    inode_pct = inode.get("used_pct", 0)
    if inode_pct >= INODE_CRIT:
        score -= 30
        critical += 1
        issues.append(f"INODE CRITICAL: {inode_pct}% used")
    elif inode_pct >= INODE_WARN:
        score -= 15
        warnings += 1
        issues.append(f"INODE WARNING: {inode_pct}% used")

    # Database size scoring
    db_gb = db.get("size_bytes", 0) / (1024**3)
    if db_gb >= DB_CRIT_GB:
        score -= 20
        critical += 1
        issues.append(f"DB CRITICAL: {db['size_human']} (>{DB_CRIT_GB}GB)")
    elif db_gb >= DB_WARN_GB:
        score -= 10
        warnings += 1
        issues.append(f"DB WARNING: {db['size_human']} (>{DB_WARN_GB}GB)")

    # Log size scoring
    log_gb = logs.get("size_bytes", 0) / (1024**3)
    if log_gb >= LOG_CRIT_GB:
        score -= 10
        critical += 1
        issues.append(f"LOG CRITICAL: {logs['size_human']} (>{LOG_CRIT_GB}GB)")
    elif log_gb >= LOG_WARN_GB:
        score -= 5
        warnings += 1
        issues.append(f"LOG WARNING: {logs['size_human']} (>{LOG_WARN_GB}GB)")

    # Bonus: perfect conditions
    if score == 100:
        issues.append("✅ All storage metrics optimal")

    score = max(0, score)
    return {
        "score": score,
        "max_score": 100,
        "critical": critical,
        "warnings": warnings,
        "issues": issues
    }

# ─── STATE MANAGEMENT ─────────────────────────────────────

def load_previous_state():
    if os.path.exists(STORAGE_STATE):
        try:
            with open(STORAGE_STATE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_state(state):
    with open(STORAGE_STATE, 'w') as f:
        json.dump(state, f, indent=2)

def compute_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]

# ─── MAIN ─────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("OMEGA STORAGE WATCH v1.0")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)

    # Gather metrics
    storage = get_termux_storage()
    disk = storage.get("internal", {})
    inode = get_inode_usage("/data")
    db = get_db_stats()
    logs = get_log_stats()

    # Calculate score
    result = calculate_score(disk, inode, db, logs)

    # Build report
    report = {
        "timestamp": datetime.now().isoformat(),
        "version": "1.0",
        "score": result["score"],
        "max_score": 100,
        "critical": result["critical"],
        "warnings": result["warnings"],
        "issues": result["issues"],
        "storage": storage,
        "inode": inode,
        "database": db,
        "logs": logs,
        "thresholds": {
            "disk_warn": DISK_WARN,
            "disk_crit": DISK_CRIT,
            "db_warn_gb": DB_WARN_GB,
            "db_crit_gb": DB_CRIT_GB,
            "log_warn_gb": LOG_WARN_GB,
            "log_crit_gb": LOG_CRIT_GB,
            "inode_warn": INODE_WARN,
            "inode_crit": INODE_CRIT
        }
    }

    # Hash for Oracle integration
    report["hash"] = compute_hash(report)

    # Compare to previous
    prev = load_previous_state()
    if prev:
        report["previous_hash"] = prev.get("hash", "none")
        report["delta"] = result["score"] - prev.get("score", 0)
        if report["hash"] == prev.get("hash"):
            report["status"] = "No change detected"
        else:
            report["status"] = "State changed"
    else:
        report["previous_hash"] = "none"
        report["delta"] = 0
        report["status"] = "First run"

    # Save state
    save_state(report)

    # Print report
    print(f"\n📊 STORAGE SCORE: {result['score']}/100")
    print(f"   Critical: {result['critical']} | Warnings: {result['warnings']}")
    print(f"   Hash: {report['hash']}")
    print(f"   Status: {report['status']}")

    print(f"\n💾 DISK (/data):")
    print(f"   Total: {disk.get('total_human', '?')}")
    print(f"   Used:  {disk.get('used_human', '?')} ({disk.get('used_pct', 0)}%)")
    print(f"   Free:  {disk.get('free_human', '?')}")

    print(f"\n📁 INODES:")
    print(f"   Total: {inode.get('total', 0):,}")
    print(f"   Used:  {inode.get('used', 0):,} ({inode.get('used_pct', 0)}%)")
    print(f"   Free:  {inode.get('free', 0):,}")

    print(f"\n🗄️  DATABASE ({DB_PATH}):")
    print(f"   Size: {db.get('size_human', '?')}")
    print(f"   Tables: {db.get('tables', 0)} | Entries: {db.get('entries', 0):,}")

    print(f"\n📋 LOGS ({LOG_DIR}):")
    print(f"   Size: {logs.get('size_human', '?')}")
    print(f"   Files: {logs.get('files', 0)}")
    print(f"   Largest: {logs.get('largest_file', 'N/A')}")

    if result["issues"]:
        print(f"\n⚠️  ISSUES:")
        for issue in result["issues"]:
            print(f"   {issue}")

    print("\n" + "=" * 60)

    # Return score for Oracle integration
    return result["score"]

if __name__ == "__main__":
    score = main()
    sys.exit(0 if score >= 80 else 1)
