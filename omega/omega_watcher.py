#!/usr/bin/env python3
"""
=============================================================
OMEGA PHONE 2 — Git Watcher Daemon
=============================================================
Watches Omega directories, detects changes, commits + pushes
to GitHub, and sends Telegram notifications.

NO architecture changes. NO DB writes. ONLY:
  - filesystem diff
  - git add/commit/push
  - Telegram alerts

Run via:
  nohup python omega_watcher.py > omega_watcher.log 2>&1 &
=============================================================
"""

import os
import sys
import time
import hashlib
import json
import subprocess
import logging
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("omega_watcher.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("omega_watcher")

# =============================================================
# CONFIG
# =============================================================

GITHUB_REPO   = os.getenv("GITHUB_REPO",   "https://github.com/cipherxsniper/omega-fintech")
GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN",  "")
BOT_TOKEN     = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID       = os.getenv("TELEGRAM_CHAT_ID",   "")
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "300"))

_watch_raw    = os.getenv("WATCH_PATHS", os.path.expanduser("~/Omega-Production"))
WATCH_PATHS   = [p.strip() for p in _watch_raw.split(",") if p.strip()]

IGNORE_DIRS   = {".git", "__pycache__", "node_modules", ".mypy_cache", ".pytest_cache"}
IGNORE_EXTS   = {".pyc", ".pyo", ".log", ".tmp"}

STATE_FILE    = os.path.expanduser("~/.omega_watcher_state.json")


# =============================================================
# TELEGRAM NOTIFICATIONS
# =============================================================

def telegram_send(message: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        log.warning("Telegram not configured — skipping notification.")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message[:4096],
        "parse_mode": "HTML",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        log.error(f"Telegram send failed: {e}")
        return False


# =============================================================
# FILESYSTEM HASHING
# =============================================================

def file_hash(path: str) -> str:
    """SHA256 hash of file contents."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def scan_directory(root: str) -> dict:
    """
    Returns {relative_path: sha256_hash} for all trackable files under root.
    """
    result = {}
    root_path = Path(root)
    if not root_path.exists():
        log.warning(f"Watch path not found: {root}")
        return result

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored dirs in-place
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in IGNORE_EXTS:
                continue
            full = os.path.join(dirpath, fname)
            rel  = os.path.relpath(full, root)
            result[rel] = file_hash(full)

    return result


# =============================================================
# STATE PERSISTENCE
# =============================================================

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"State load error: {e}")
    return {}


def save_state(state: dict):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log.error(f"State save error: {e}")


# =============================================================
# DIFF ENGINE
# =============================================================

def compute_diff(old_state: dict, new_state: dict) -> dict:
    """
    Returns:
      {
        "created":  [path, ...],
        "modified": [path, ...],
        "deleted":  [path, ...],
      }
    """
    old_keys = set(old_state.keys())
    new_keys = set(new_state.keys())

    created  = sorted(new_keys - old_keys)
    deleted  = sorted(old_keys - new_keys)
    modified = sorted(
        k for k in (old_keys & new_keys)
        if old_state[k] != new_state[k]
    )

    return {"created": created, "modified": modified, "deleted": deleted}


# =============================================================
# GIT SYNC
# =============================================================

def _run_git(cmd: list, cwd: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "git command timed out"
    except Exception as e:
        return False, str(e)


def git_push_changes(repo_path: str, message: str, retries: int = 3) -> bool:
    """
    Stages, commits, and pushes changes from repo_path.
    Returns True on success.
    """
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        log.warning(f"Not a git repo: {repo_path}")
        return False

    # Stage all changes
    ok, out = _run_git(["git", "add", "-A"], cwd=repo_path)
    if not ok:
        log.error(f"git add failed: {out}")
        return False

    # Check if anything to commit
    ok, status = _run_git(["git", "status", "--porcelain"], cwd=repo_path)
    if not status.strip():
        log.info("No changes to commit.")
        return True

    # Commit
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    commit_msg = f"[omega-watcher] {message} @ {ts}"
    ok, out = _run_git(["git", "commit", "-m", commit_msg], cwd=repo_path)
    if not ok:
        log.error(f"git commit failed: {out}")
        return False
    log.info(f"Git commit: {commit_msg}")

    # Push with retry
    for attempt in range(1, retries + 1):
        ok, out = _run_git(["git", "push"], cwd=repo_path)
        if ok:
            log.info(f"Git push successful (attempt {attempt})")
            return True
        log.warning(f"Git push attempt {attempt} failed: {out}")
        time.sleep(5 * attempt)

    log.error("Git push failed after all retries.")
    return False


def find_git_root(watch_paths: list) -> str | None:
    """
    Find the first git repo root among or above the watch paths.
    Avoids nested repo confusion.
    """
    for wp in watch_paths:
        candidate = wp
        while candidate != os.path.dirname(candidate):
            if os.path.isdir(os.path.join(candidate, ".git")):
                return candidate
            candidate = os.path.dirname(candidate)
    return None


# =============================================================
# MAIN WATCHER LOOP
# =============================================================

def build_change_summary(diff: dict, watch_path: str) -> str:
    created  = diff["created"]
    modified = diff["modified"]
    deleted  = diff["deleted"]
    total    = len(created) + len(modified) + len(deleted)
    ts       = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"📡 <b>OMEGA FILE CHANGE</b>",
        f"Path: <code>{watch_path}</code>",
        f"Time: {ts}",
        f"Total changes: {total}",
    ]
    if created:
        lines.append(f"\n🟢 Created ({len(created)}):")
        for f in created[:8]:
            lines.append(f"  • {f}")
    if modified:
        lines.append(f"\n🟡 Modified ({len(modified)}):")
        for f in modified[:8]:
            lines.append(f"  • {f}")
    if deleted:
        lines.append(f"\n🔴 Deleted ({len(deleted)}):")
        for f in deleted[:8]:
            lines.append(f"  • {f}")
    return "\n".join(lines)


def run():
    log.info("=" * 60)
    log.info("OMEGA WATCHER DAEMON STARTING")
    log.info(f"Watch paths: {WATCH_PATHS}")
    log.info(f"Scan interval: {SCAN_INTERVAL}s")
    log.info("=" * 60)

    telegram_send("🟢 <b>OMEGA WATCHER ONLINE</b>\nFile watcher daemon started.")

    git_root = find_git_root(WATCH_PATHS)
    if git_root:
        log.info(f"Git root detected: {git_root}")
    else:
        log.warning("No git root found — git push disabled.")

    # Load last known state
    state = load_state()

    while True:
        try:
            log.info("--- Scan cycle starting ---")

            for watch_path in WATCH_PATHS:
                if not os.path.exists(watch_path):
                    log.warning(f"Path missing: {watch_path}")
                    continue

                old_scan = state.get(watch_path, {})
                new_scan = scan_directory(watch_path)
                diff     = compute_diff(old_scan, new_scan)

                total_changes = (
                    len(diff["created"]) +
                    len(diff["modified"]) +
                    len(diff["deleted"])
                )

                if total_changes == 0:
                    log.info(f"No changes in {watch_path}")
                    state[watch_path] = new_scan
                    continue

                log.info(
                    f"Changes in {watch_path}: "
                    f"+{len(diff['created'])} ~{len(diff['modified'])} -{len(diff['deleted'])}"
                )

                # Send Telegram notification
                summary = build_change_summary(diff, watch_path)
                telegram_send(summary)

                # Git push
                if git_root:
                    push_msg = (
                        f"{total_changes} changes: "
                        f"+{len(diff['created'])} ~{len(diff['modified'])} -{len(diff['deleted'])}"
                    )
                    success = git_push_changes(git_root, push_msg)
                    if success:
                        telegram_send(
                            f"✅ <b>GIT PUSH SUCCESS</b>\n"
                            f"Repo: {git_root}\n"
                            f"Changes: {push_msg}"
                        )
                    else:
                        telegram_send(
                            f"❌ <b>GIT PUSH FAILED</b>\n"
                            f"Repo: {git_root}\n"
                            f"Changes were detected but push failed. Check logs."
                        )

                # Update state
                state[watch_path] = new_scan

            save_state(state)
            log.info(f"Scan complete. Sleeping {SCAN_INTERVAL}s...")

        except KeyboardInterrupt:
            log.info("Watcher stopped by user.")
            telegram_send("🔴 <b>OMEGA WATCHER STOPPED</b>")
            break
        except Exception as e:
            log.error(f"Watcher loop error: {e}", exc_info=True)
            telegram_send(f"⚠️ <b>OMEGA WATCHER ERROR</b>\n{str(e)[:200]}")

        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    run()
