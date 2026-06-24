#!/usr/bin/env python3
"""
OMEGA STORAGE VERIFICATION ENGINE
Periodically measures real disk usage on both phones and updates
the omega_cloud_node3.db registry with verified numbers.

No fiction. No placeholders. Every number is measured at runtime.
"""
import sqlite3, subprocess, re
from datetime import datetime, timezone

DB_PATH = "/data/data/com.termux/files/home/omega_cloud_node3.db"

def get_local_disk():
    """Measure Phone 1 disk usage."""
    try:
        out = subprocess.run(
            ["df", "-h", "/data/data/com.termux/files/home"],
            capture_output=True, text=True, timeout=10
        ).stdout
        # Parse the data line (second line)
        lines = out.strip().split("\n")
        if len(lines) < 2:
            return None
        parts = lines[1].split()
        # Filesystem Size Used Avail Use% Mounted
        size, used, avail = parts[1], parts[2], parts[3]
        return {
            "total_gb": _to_gb(size),
            "used_gb": _to_gb(used),
            "avail_gb": _to_gb(avail),
        }
    except Exception as e:
        print(f"Local disk check failed: {e}")
        return None

def get_remote_disk():
    """Measure Phone 2 disk usage via SSH."""
    try:
        out = subprocess.run(
            ["ssh", "-i", "/data/data/com.termux/files/home/.ssh/omega_bridge",
             "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
             "u0_a253@192.168.11.163", "-p", "8022",
             "df -h /data/data/com.termux/files/home"],
            capture_output=True, text=True, timeout=15
        ).stdout
        lines = out.strip().split("\n")
        if len(lines) < 2:
            return None
        parts = lines[1].split()
        size, used, avail = parts[1], parts[2], parts[3]
        return {
            "total_gb": _to_gb(size),
            "used_gb": _to_gb(used),
            "avail_gb": _to_gb(avail),
        }
    except Exception as e:
        print(f"Remote disk check failed: {e}")
        return None

def _to_gb(s):
    """Convert df -h size string (e.g. '68G', '6.6G', '512M') to GB float."""
    s = s.strip()
    m = re.match(r"([\d.]+)([GMKT]?)", s)
    if not m:
        return 0.0
    val, unit = float(m.group(1)), m.group(2)
    if unit == "T":
        return val * 1024
    elif unit == "G":
        return val
    elif unit == "M":
        return val / 1024
    elif unit == "K":
        return val / (1024 * 1024)
    return val

def update_registry(node_id, disk_data):
    if not disk_data:
        print(f"  {node_id}: SKIP (no data)")
        return False
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        UPDATE omega_nodes
        SET storage_total_gb=?, storage_used_gb=?, storage_available_gb=?, last_verified=?
        WHERE node_id=?
    """, (disk_data["total_gb"], disk_data["used_gb"], disk_data["avail_gb"], now, node_id))
    conn.commit()
    conn.close()
    print(f"  {node_id}: total={disk_data['total_gb']:.1f}GB used={disk_data['used_gb']:.1f}GB avail={disk_data['avail_gb']:.1f}GB")
    return True

def run_verification():
    print(f"=== Omega Storage Verification — {datetime.now(timezone.utc).isoformat()} ===")

    print("Phone 1 (omega-node-001):")
    p1 = get_local_disk()
    update_registry("omega-node-001", p1)

    print("Phone 2 (omega-node-002):")
    p2 = get_remote_disk()
    update_registry("omega-node-002", p2)

    # Compute totals
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("""
        SELECT SUM(storage_total_gb), SUM(storage_used_gb), SUM(storage_available_gb)
        FROM omega_nodes WHERE node_type='phone_node'
    """).fetchone()
    conn.close()

    if row and row[0]:
        print(f"\nVerified network totals:")
        print(f"  Total capacity:  {row[0]:.1f}GB")
        print(f"  Used:            {row[1]:.1f}GB")
        print(f"  Available:       {row[2]:.1f}GB")

    return p1 is not None and p2 is not None

if __name__ == "__main__":
    run_verification()
