#!/usr/bin/env python3
"""
OMEGA DISASTER RECOVERY ENGINE v1.0
Backs up critical system files, stores them via OmegaStorage on the
OTHER phone (cross-node redundancy), with SHA-256 checksum proof.

If Phone 1 dies completely, Phone 2 holds a checksummed, encrypted
copy of everything needed to rebuild it. And vice versa.

This is real disaster recovery — not a wallet, not a token, not a
node. A backup file with a mathematical proof of integrity.
"""
import os, sys, json, tarfile, hashlib, subprocess, tempfile
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
sys.path.insert(0, str(HOME / "omega_runtime"))

# Files/dirs to back up — code, configs, schemas. NOT the live databases.
BACKUP_TARGETS = [
    "omega_v10.py",
    "omega_oracle_v2.py",
    "omega_oracle_history.json",
    "omega_consensus.py" if (HOME / "omega_consensus.py").exists() else None,
    "Omega-Production/omega_consensus.py",
    "omega_sentinel.py",
    "omega_card_engine.py",
    "omega_email_finder.py",
    "omega_scraper.py",
    "omega_spawn_engine.py",
    "omega_storage_verify.py",
    "omega_guardian.sh",
    "omega_tunnel_daemon.sh",
    "omega_start.sh",
    "omega_treasury_cycle.py",
    "omega_node_manager.py",
    "omega_cloud_node3_api_server.py",
    "omega_runtime/omega_storage.py",
    "omega_runtime/omega_auth.py",
    "omega_runtime/omega_http_server.py",
    "omega_runtime/omega_tls_server.py",
]

LOG_PATH = HOME / "omega_runtime/logs/disaster_recovery.log"

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")

def build_backup_tarball() -> Path:
    """Create a tar.gz of all backup targets that exist."""
    tmp = Path(tempfile.mktemp(suffix=".tar.gz"))
    included = []
    with tarfile.open(tmp, "w:gz") as tar:
        for target in BACKUP_TARGETS:
            if target is None:
                continue
            path = HOME / target
            if path.exists():
                tar.add(path, arcname=target)
                included.append(target)
            else:
                log(f"  skip (not found): {target}")
    log(f"Backup tarball built: {len(included)} files included")
    return tmp

def store_local_copy(tarball: Path) -> dict:
    """Store backup via local OmegaStorage (this phone's storage)."""
    from omega_storage import OmegaStorage
    data = tarball.read_bytes()
    meta = OmegaStorage.put(
        owner_id="thomas_lee_harvey",
        object_name=f"system_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.tar.gz",
        data=data,
        content_type="application/gzip",
        immutable=True,
    )
    return meta

def store_remote_copy(tarball: Path, remote_host: str, remote_port: int = 8022,
                       remote_user: str = "u0_a253",
                       ssh_key: str = "~/.ssh/omega_bridge") -> dict:
    """
    Copy tarball to the OTHER phone via scp, then trigger remote
    OmegaStorage.put() via ssh — true cross-node redundancy.
    """
    remote_tmp = "/data/data/com.termux/files/home/omega_runtime/tmp_backup.tar.gz"
    ssh_key_path = os.path.expanduser(ssh_key)

    # Copy the file over
    scp_cmd = [
        "scp", "-i", ssh_key_path, "-o", "StrictHostKeyChecking=no",
        "-P", str(remote_port),
        str(tarball),
        f"{remote_user}@{remote_host}:{remote_tmp}"
    ]
    result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        log(f"  scp failed: {result.stderr.strip()}")
        return {"ok": False, "error": result.stderr.strip()}

    # Trigger remote storage via a small inline python script
    backup_name = f"system_backup_from_phone1_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.tar.gz"
    remote_script_lines = [
        "import sys",
        'sys.path.insert(0, "/data/data/com.termux/files/home/omega_runtime")',
        "from omega_storage import OmegaStorage",
        f'data = open("{remote_tmp}", "rb").read()',
        "meta = OmegaStorage.put(",
        '    owner_id="thomas_lee_harvey",',
        f'    object_name="{backup_name}",',
        "    data=data,",
        '    content_type="application/gzip",',
        "    immutable=True,",
        ")",
        "import os",
        f'os.remove("{remote_tmp}")',
        'print(meta["object_id"] + "|" + meta["checksum"])',
    ]
    remote_script = "\n".join(remote_script_lines) + "\n"

    # Write remote script to local temp file, scp it over, then execute it
    local_script_path = Path(tempfile.mktemp(suffix=".py"))
    local_script_path.write_text(remote_script)
    remote_script_path = "/data/data/com.termux/files/home/omega_runtime/tmp_backup_store.py"

    scp_script_cmd = [
        "scp", "-i", ssh_key_path, "-o", "StrictHostKeyChecking=no",
        "-P", str(remote_port),
        str(local_script_path),
        f"{remote_user}@{remote_host}:{remote_script_path}"
    ]
    subprocess.run(scp_script_cmd, capture_output=True, text=True, timeout=30)
    local_script_path.unlink(missing_ok=True)

    ssh_cmd = [
        "ssh", "-i", ssh_key_path, "-o", "StrictHostKeyChecking=no",
        "-p", str(remote_port),
        f"{remote_user}@{remote_host}",
        f"python3 {remote_script_path} && rm -f {remote_script_path}"
    ]
    result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        log(f"  remote store failed: {result.stderr.strip()}")
        return {"ok": False, "error": result.stderr.strip()}

    output = result.stdout.strip()
    if "|" not in output:
        log(f"  unexpected remote output: {output}")
        return {"ok": False, "error": output}

    object_id, checksum = output.split("|")
    return {"ok": True, "object_id": object_id, "checksum": checksum, "host": remote_host}

def run_backup():
    log("=" * 50)
    log("OMEGA DISASTER RECOVERY — BACKUP RUN")
    log("=" * 50)

    tarball = build_backup_tarball()
    tarball_hash = hashlib.sha256(tarball.read_bytes()).hexdigest()
    tarball_size = tarball.stat().st_size
    log(f"Tarball: {tarball_size} bytes, sha256={tarball_hash[:16]}...")

    # Local copy
    local_meta = store_local_copy(tarball)
    log(f"Local copy stored: object_id={local_meta['object_id']} checksum={local_meta['checksum'][:16]}...")

    # Remote copy — cross-node redundancy
    remote_result = store_remote_copy(tarball, remote_host="192.168.11.163")
    if remote_result.get("ok"):
        log(f"Remote copy stored on 192.168.11.163: object_id={remote_result['object_id']} checksum={remote_result['checksum'][:16]}...")
    else:
        log(f"Remote copy FAILED: {remote_result.get('error')}")

    tarball.unlink(missing_ok=True)

    result = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tarball_sha256": tarball_hash,
        "tarball_size": tarball_size,
        "local": local_meta,
        "remote": remote_result,
    }

    # Save run record
    record_path = HOME / "omega_runtime/state/last_backup.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(result, indent=2, default=str))

    # Copy backup record + tarball hash pointer into git repo for GitHub redundancy
    repo_backup_dir = HOME / "omega_backups"
    repo_backup_dir.mkdir(parents=True, exist_ok=True)
    repo_record_path = repo_backup_dir / "latest_backup.json"
    repo_record_path.write_text(json.dumps({
        "ts": result["ts"],
        "tarball_sha256": result["tarball_sha256"],
        "tarball_size": result["tarball_size"],
        "local_object_id": local_meta["object_id"],
        "local_checksum": local_meta["checksum"],
        "remote_object_id": remote_result.get("object_id"),
        "remote_checksum": remote_result.get("checksum"),
        "remote_host": remote_result.get("host"),
        "files_backed_up": BACKUP_TARGETS,
    }, indent=2, default=str))
    log(f"GitHub backup pointer written: {repo_record_path}")

    log("=" * 50)
    log(f"BACKUP COMPLETE — local={'OK' if local_meta else 'FAIL'} remote={'OK' if remote_result.get('ok') else 'FAIL'} github_pointer=OK")
    log("=" * 50)
    return result

def verify_last_backup():
    """Verify the most recent local backup's checksum still matches."""
    from omega_storage import OmegaStorage
    record_path = HOME / "omega_runtime/state/last_backup.json"
    if not record_path.exists():
        print("No backup record found. Run: python3 omega_disaster_recovery.py backup")
        return False

    record = json.loads(record_path.read_text())
    object_id = record["local"]["object_id"]
    data, meta = OmegaStorage.get(object_id, "thomas_lee_harvey")
    if data is None:
        print(f"❌ Backup object {object_id} not found or checksum mismatch")
        return False

    actual_hash = hashlib.sha256(data).hexdigest()
    expected_hash = record["tarball_sha256"]
    if actual_hash == expected_hash:
        print(f"✅ Backup verified — checksum matches: {actual_hash[:16]}...")
        print(f"   Created: {record['ts']}")
        print(f"   Size: {record['tarball_size']} bytes")
        return True
    else:
        print(f"❌ CHECKSUM MISMATCH — backup may be corrupted")
        print(f"   Expected: {expected_hash[:16]}...")
        print(f"   Actual:   {actual_hash[:16]}...")
        return False

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "backup"
    if cmd == "backup":
        run_backup()
    elif cmd == "verify":
        verify_last_backup()
    else:
        print("Usage: python3 omega_disaster_recovery.py [backup|verify]")
