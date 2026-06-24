#!/usr/bin/env python3
"""
omega_dreamer.py — Autonomous Overnight Build Agent
====================================================
Runs while Thomas sleeps. Watches the system, generates patches,
scores before and after, only commits if score improves.
Pushes to GitHub automatically on every proven improvement.

Rules (hardcoded, never overridden):
  • Never touch omega_bank DB, omega_ledger DB, ledger_entries
  • Never touch omega_consensus.py or omega_node_manager.py
  • Score must be strictly higher after patch or revert + skip
  • Max patches per session configurable (default 10)
  • Telegram report to Thomas after every patch attempt
  • Full session summary sent at wake-up time

Usage:
  python3 omega_dreamer.py run          # start overnight session
  python3 omega_dreamer.py status       # show last session log
  python3 omega_dreamer.py plan         # show what it would do tonight
"""

import os, sys, json, time, shutil, hashlib, subprocess, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
HOME          = Path("/data/data/com.termux/files/home")
DREAMER_LOG   = HOME / "omega_dreamer_log.json"
DREAMER_LOCK  = HOME / "omega_dreamer.lock"
BACKUP_DIR    = HOME / "omega_dreamer_backups"
BACKUP_DIR.mkdir(exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TELEGRAM_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID", "8620185302")
ORACLE_PATH       = HOME / "omega_oracle_v2.py"
OPS_PATH          = HOME / "OMEGABACK1/20260614_041203/ops_engine.py"
PUSH_CMD          = "push"   # your .bashrc alias

MAX_PATCHES       = int(os.getenv("DREAMER_MAX_PATCHES", 10))
MIN_SCORE_DELTA   = int(os.getenv("DREAMER_MIN_DELTA", 1))   # must improve by at least this

# ---------------------------------------------------------------------------
# Absolute no-touch list — hardcoded, never passed to Claude as editable
# ---------------------------------------------------------------------------
FORBIDDEN_FILES = {
    "omega_consensus.py",
    "omega_node_manager.py",
}
FORBIDDEN_PATTERNS = [
    "DROP TABLE",
    "DROP DATABASE",
    "TRUNCATE TABLE",
    "DELETE FROM ledger_entries",
    "UPDATE ledger_entries",
    "ALTER TABLE ledger_entries",
    "dbname='omega_bank'",
    "dbname='omega_ledger'",
    "psycopg2.connect",
    "os.system('rm",
    "shutil.rmtree",
]

# ---------------------------------------------------------------------------
# Watched assets — what the dreamer monitors and can report on
# ---------------------------------------------------------------------------
WATCHED_URLS = {
    "node3_health":    "http://127.0.0.1:5004/health",
    "node3_stats":     "http://127.0.0.1:5004/v1/storage/stats",
    "guardian_health": "http://127.0.0.1:5004/health",
}

WATCHED_FILES = [
    HOME / "omega_v10.py",
    HOME / "omega_oracle_v2.py",
    HOME / "omega_sentinel.py",
    HOME / "omega_card_engine.py",
    HOME / "omega_email_finder.py",
    HOME / "omega_runtime/omega_http_server.py",
    HOME / "omega_runtime/omega_storage.py",
    HOME / "omega_runtime/omega_auth.py",
    HOME / "omega_dreamer.py",
]

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
def telegram(msg: str):
    if not TELEGRAM_TOKEN:
        print(f"[TELEGRAM] {msg}")
        return
    try:
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text":    f"🤖 *Omega Dreamer*\n{msg}",
            "parse_mode": "Markdown"
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

# ---------------------------------------------------------------------------
# System observation — what the dreamer sees before deciding what to build
# ---------------------------------------------------------------------------
def observe_system() -> dict:
    """Full system snapshot: scores, file sizes, endpoint health, issues."""
    obs = {
        "ts":         datetime.now(timezone.utc).isoformat(),
        "endpoints":  {},
        "files":      {},
        "oracle":     {},
        "issues":     [],
    }

    # Endpoint health
    bearer = os.getenv("NODE3_BEARER_TOKEN",
                        "nk6ru6pp-4xAvSpM3ZFlust42ZiCbDVtLgF8Z44zoh0")
    for name, url in WATCHED_URLS.items():
        try:
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {bearer}"})
            res = urllib.request.urlopen(req, timeout=5)
            obs["endpoints"][name] = {
                "status": res.status, "ok": True,
                "body":   json.loads(res.read().decode())
            }
        except urllib.error.HTTPError as e:
            obs["endpoints"][name] = {"status": e.code, "ok": False}
        except Exception as e:
            obs["endpoints"][name] = {"ok": False, "error": str(e)}

    # File inventory
    for f in WATCHED_FILES:
        if f.exists():
            src  = f.read_text(errors="replace")
            obs["files"][f.name] = {
                "lines": src.count("\n") + 1,
                "size":  f.stat().st_size,
                "hash":  hashlib.sha256(src.encode()).hexdigest()[:16],
            }
        else:
            obs["files"][f.name] = {"exists": False}
            obs["issues"].append(f"MISSING: {f.name}")

    # Oracle score (quick parse from history)
    history_file = HOME / "omega_oracle_history.json"
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text())
            if history:
                last = history[-1]
                obs["oracle"] = {
                    "score":       last.get("total", 0),
                    "grade":       last.get("grade", "?"),
                    "patch_count": last.get("patch_count", 0),
                    "components":  last.get("components", {}),
                    "ts":          last.get("ts", ""),
                }
                # Flag any component below 100
                for comp, score in last.get("components", {}).items():
                    if score < 100:
                        obs["issues"].append(
                            f"BELOW_100: {comp} = {score}/100")
        except Exception as e:
            obs["oracle"] = {"error": str(e)}

    return obs

# ---------------------------------------------------------------------------
# Oracle scoring
# ---------------------------------------------------------------------------
def run_oracle_score() -> Optional[int]:
    """Run oracle_v3.py score, return integer total or None on failure."""
    if not ORACLE_PATH.exists():
        return None
    try:
        result = subprocess.run(
            ["python3", str(ORACLE_PATH), "score"],
            capture_output=True, text=True, timeout=120,
            cwd=str(HOME)
        )
        output = result.stdout + result.stderr
        import re
        m = re.search(r"SYSTEM SCORE:\s*(\d+)/100", output)
        return int(m.group(1)) if m else None
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Safety gate — scan patch content before applying
# ---------------------------------------------------------------------------
def is_patch_safe(filename: str, new_content: str) -> tuple[bool, str]:
    if filename in FORBIDDEN_FILES:
        return False, f"FORBIDDEN FILE: {filename}"
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in new_content.lower():
            return False, f"FORBIDDEN PATTERN: '{pattern}'"
    # Must be valid Python if .py file
    if filename.endswith(".py"):
        import ast
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            return False, f"SYNTAX ERROR: line {e.lineno} — {e.msg}"
    return True, "OK"

# ---------------------------------------------------------------------------
# Claude API call (raw urllib, no SDK)
# ---------------------------------------------------------------------------
def call_claude(system_prompt: str, user_prompt: str,
                max_tokens: int = 4096) -> Optional[str]:
    if not ANTHROPIC_API_KEY:
        print("[DREAMER] No ANTHROPIC_API_KEY in env")
        return None
    try:
        payload = json.dumps({
            "model":      "claude-sonnet-4-6",
            "max_tokens": max_tokens,
            "system":     system_prompt,
            "messages":   [{"role": "user", "content": user_prompt}]
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key":         ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            method="POST"
        )
        res  = urllib.request.urlopen(req, timeout=120)
        data = json.loads(res.read().decode())
        return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        print(f"[CLAUDE ERROR] HTTP {e.code}: {e.read().decode()[:300]}")
        return None
    except Exception as e:
        print(f"[CLAUDE ERROR] {e}")
        return None

# ---------------------------------------------------------------------------
# Patch extraction — Claude returns structured JSON
# ---------------------------------------------------------------------------
def extract_patch(response: str) -> Optional[dict]:
    """
    Claude must return JSON with this exact structure:
    {
        "filename": "omega_v10.py",
        "description": "What this patch does",
        "reasoning": "Why this improves the system",
        "content": "<full file content>"
    }
    """
    import re
    # Try direct JSON parse first
    try:
        return json.loads(response)
    except Exception:
        pass
    # Try to extract JSON block
    m = re.search(r'\{[\s\S]*"filename"[\s\S]*"content"[\s\S]*\}', response)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None

# ---------------------------------------------------------------------------
# Apply patch with backup + revert capability
# ---------------------------------------------------------------------------
def apply_patch(patch: dict) -> tuple[bool, str]:
    filename    = patch.get("filename", "")
    new_content = patch.get("content", "")
    target      = HOME / filename

    # Backup original
    backup_path = BACKUP_DIR / f"{filename}.{int(time.time())}.bak"
    if target.exists():
        shutil.copy2(target, backup_path)

    # Write new content
    target.write_text(new_content, encoding="utf-8")
    return True, str(backup_path)

def revert_patch(filename: str, backup_path: str):
    target = HOME / filename
    if Path(backup_path).exists():
        shutil.copy2(backup_path, target)
        print(f"[DREAMER] Reverted {filename} from {backup_path}")

# ---------------------------------------------------------------------------
# Git push
# ---------------------------------------------------------------------------
def git_push(description: str):
    try:
        result = subprocess.run(
            ["bash", "-c", "push"],
            capture_output=True, text=True, timeout=60,
            cwd=str(HOME)
        )
        if result.returncode == 0:
            print(f"[DREAMER] Pushed to GitHub: {description}")
            return True
        else:
            print(f"[DREAMER] Push failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"[DREAMER] Push error: {e}")
        return False

# ---------------------------------------------------------------------------
# Session log
# ---------------------------------------------------------------------------
def load_log() -> list:
    if DREAMER_LOG.exists():
        try: return json.loads(DREAMER_LOG.read_text())
        except: pass
    return []

def save_log(entries: list):
    DREAMER_LOG.write_text(json.dumps(entries, indent=2))

def log_entry(session_id: str, data: dict):
    entries = load_log()
    entries.append({"session_id": session_id, **data,
                    "ts": datetime.now(timezone.utc).isoformat()})
    if len(entries) > 500:
        entries = entries[-500:]
    save_log(entries)

# ---------------------------------------------------------------------------
# Core decision loop — one patch cycle
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are the Omega Dreamer — an autonomous build agent for Thomas Lee Harvey's
Omega AI system. Thomas is asleep. You are running overnight to improve his production system.

YOUR IDENTITY:
- You are motivated, innovative, and technically excellent
- You think architecturally and make decisions Thomas would be proud of
- You are a guardian of the system's integrity

ABSOLUTE RULES — NEVER VIOLATE:
1. Never modify omega_consensus.py or omega_node_manager.py
2. Never touch omega_bank database, omega_ledger database, or ledger_entries table
3. Never add third-party dependencies — urllib only, pure Python, no pip installs
4. Never use pydantic, Anthropic SDK, or any external API keys except those in .env
5. All string literals use \\n explicitly — never literal newlines inside quotes
6. The Oracle score must improve after your patch or it gets reverted automatically

WHAT YOU CAN DO:
- Improve omega_v10.py (4500+ lines, Telegram bot, revenue OS)
- Enhance omega_sentinel.py (drift detection, 160 functions)
- Upgrade oracle_v3.py scoring dimensions
- Improve omega_email_finder.py or omega_card_engine.py
- Add new endpoints to omega_node3_server.py
- Improve omega_runtime/omega_storage.py or omega_auth.py
- Write new utility scripts that add real capability
- Fix any issues the Oracle flagged
- Add monitoring, alerting, or self-healing logic

PATCH FORMAT — respond ONLY with valid JSON, no markdown, no explanation outside:
{
    "filename": "relative/path/from/home/file.py",
    "description": "One line — what this does",
    "reasoning": "Why this improves the Oracle score or system capability",
    "content": "FULL FILE CONTENT HERE — complete replacement, not a diff"
}

The Oracle scores these components with these weights:
  omega_v10 40%, omega_consensus 10%, omega_sentinel 10%, oracle_v3 10%,
  omega_email_finder 5%, omega_card_engine 5%, omega_guardian 5%,
  omega_bank_db 5%, omega_ledger_db 5%, omega_node3 5%

Think carefully. Pick the highest-value improvement. Be innovative."""


def dream_one_patch(session_id: str, obs: dict,
                    patch_num: int, session_history: list) -> dict:
    """One full patch cycle. Returns result dict."""
    print(f"\n[DREAMER] ━━━ Patch #{patch_num} ━━━")

    # Build context for Claude
    user_prompt = f"""SYSTEM OBSERVATION:
{json.dumps(obs, indent=2)}

PATCHES ATTEMPTED THIS SESSION:
{json.dumps(session_history, indent=2)}

CURRENT TIME: {datetime.now(timezone.utc).strftime('%H:%M UTC')}
PATCH NUMBER: {patch_num} of {MAX_PATCHES}

Based on the system state above, decide what to build or fix.
Look at the Oracle issues list, endpoint health, and file inventory.
Pick the single highest-value improvement you can make right now.
Return ONLY the JSON patch object."""

    print(f"[DREAMER] Asking Claude what to build...")
    response = call_claude(SYSTEM_PROMPT, user_prompt, max_tokens=8192)

    if not response:
        result = {"status": "error", "reason": "Claude API returned nothing"}
        log_entry(session_id, {"patch_num": patch_num, **result})
        return result

    patch = extract_patch(response)
    if not patch:
        result = {"status": "error", "reason": "Could not parse patch JSON",
                  "raw": response[:300]}
        log_entry(session_id, {"patch_num": patch_num, **result})
        return result

    filename    = patch.get("filename", "")
    description = patch.get("description", "")
    reasoning   = patch.get("reasoning", "")
    print(f"[DREAMER] Proposed: {filename}")
    print(f"[DREAMER] Reason:   {description}")

    # Safety gate
    safe, safety_msg = is_patch_safe(filename, patch.get("content", ""))
    if not safe:
        result = {"status": "blocked", "filename": filename,
                  "reason": safety_msg}
        log_entry(session_id, {"patch_num": patch_num, **result})
        telegram(f"⛔ Patch #{patch_num} BLOCKED\n`{filename}`\n{safety_msg}")
        return result

    # Score BEFORE
    print(f"[DREAMER] Scoring BEFORE...")
    score_before = run_oracle_score()
    if score_before is None:
        result = {"status": "error", "reason": "Oracle not found — oracle_v2.py missing or broken", "filename": filename}
        log_entry(session_id, {"patch_num": patch_num, **result})
        telegram(f"❌ Patch #{patch_num} — Oracle unreachable, skipping `{filename}`")
        return result
    print(f"[DREAMER] Score before: {score_before}/100")

    # Apply patch
    applied, backup_path = apply_patch(patch)
    print(f"[DREAMER] Applied patch → {filename} (backup: {backup_path})")

    # Score AFTER
    print(f"[DREAMER] Scoring AFTER...")
    time.sleep(2)   # let filesystem settle
    score_after = run_oracle_score()

    if score_after is None:
        revert_patch(filename, backup_path)
        result = {"status": "reverted", "filename": filename,
                  "reason": "Oracle failed after patch"}
        log_entry(session_id, {"patch_num": patch_num, **result})
        telegram(f"↩️ Patch #{patch_num} REVERTED (oracle failure)\n`{filename}`")
        return result

    delta = score_after - score_before
    print(f"[DREAMER] Score after:  {score_after}/100  (Δ {'+' if delta >= 0 else ''}{delta})")

    if delta < MIN_SCORE_DELTA:
        revert_patch(filename, backup_path)
        result = {
            "status":       "reverted",
            "filename":     filename,
            "description":  description,
            "score_before": score_before,
            "score_after":  score_after,
            "delta":        delta,
            "reason":       f"Score did not improve by {MIN_SCORE_DELTA} (got {delta})",
        }
        log_entry(session_id, {"patch_num": patch_num, **result})
        telegram(f"↩️ Patch #{patch_num} REVERTED (score {score_before}→{score_after})\n"
                 f"`{filename}`\n_{description}_")
        return result

    # ACCEPTED — push to GitHub
    print(f"[DREAMER] ✅ PATCH ACCEPTED  {score_before} → {score_after} (+{delta})")
    pushed = git_push(f"[dreamer] #{patch_num}: {description}")

    result = {
        "status":       "accepted",
        "filename":     filename,
        "description":  description,
        "reasoning":    reasoning,
        "score_before": score_before,
        "score_after":  score_after,
        "delta":        delta,
        "pushed":       pushed,
    }
    log_entry(session_id, {"patch_num": patch_num, **result})
    telegram(f"✅ Patch #{patch_num} ACCEPTED  {score_before}→{score_after} (+{delta})\n"
             f"`{filename}`\n_{description}_\n"
             f"{'📤 Pushed to GitHub' if pushed else '⚠️ Push failed'}")
    return result

# ---------------------------------------------------------------------------
# Full overnight session
# ---------------------------------------------------------------------------
def run_session():
    if DREAMER_LOCK.exists():
        print("[DREAMER] Lock file exists — already running. Exiting.")
        sys.exit(1)

    session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    DREAMER_LOCK.write_text(session_id)

    print(f"\n{'▓'*58}")
    print(f"  OMEGA DREAMER — Session {session_id}")
    print(f"  Max patches: {MAX_PATCHES}  |  Min delta: {MIN_SCORE_DELTA}")
    print(f"{'▓'*58}\n")

    telegram(f"🌙 Dreamer session started\n"
             f"Session: `{session_id}`\n"
             f"Max patches: {MAX_PATCHES}")

    session_history = []
    accepted        = 0
    reverted        = 0
    blocked         = 0

    try:
        for patch_num in range(1, MAX_PATCHES + 1):
            # Fresh observation each cycle
            obs    = observe_system()
            result = dream_one_patch(session_id, obs, patch_num,
                                     session_history)
            session_history.append({
                "patch_num":   patch_num,
                "status":      result.get("status"),
                "filename":    result.get("filename", ""),
                "description": result.get("description", ""),
                "delta":       result.get("delta", 0),
            })

            if result["status"] == "accepted":
                accepted += 1
            elif result["status"] == "reverted":
                reverted += 1
            elif result["status"] == "blocked":
                blocked  += 1

            # Cool down between patches
            if patch_num < MAX_PATCHES:
                print(f"[DREAMER] Cooling down 30s...")
                time.sleep(30)

    except KeyboardInterrupt:
        print("\n[DREAMER] Interrupted by user.")
    finally:
        DREAMER_LOCK.unlink(missing_ok=True)

    # Final score
    final_score = run_oracle_score()

    summary = (
        f"☀️ Dreamer session complete\n"
        f"Session: `{session_id}`\n"
        f"Patches: {MAX_PATCHES} attempted\n"
        f"✅ Accepted: {accepted}\n"
        f"↩️ Reverted: {reverted}\n"
        f"⛔ Blocked:  {blocked}\n"
        f"Oracle: {final_score}/100"
    )
    print(f"\n{'▓'*58}")
    print(f"  SESSION COMPLETE")
    print(f"  Accepted: {accepted}  Reverted: {reverted}  Blocked: {blocked}")
    print(f"  Final Oracle score: {final_score}/100")
    print(f"{'▓'*58}\n")
    telegram(summary)

    log_entry(session_id, {
        "type":        "session_summary",
        "accepted":    accepted,
        "reverted":    reverted,
        "blocked":     blocked,
        "final_score": final_score,
    })

# ---------------------------------------------------------------------------
# Status / plan commands
# ---------------------------------------------------------------------------
def show_status():
    entries = load_log()
    if not entries:
        print("No dreamer sessions yet.")
        return
    print(f"\n  OMEGA DREAMER — Last 10 log entries")
    print("  " + "─" * 54)
    for e in entries[-10:]:
        status = e.get("status", e.get("type", "?"))
        icon   = {"accepted": "✅", "reverted": "↩️",
                  "blocked": "⛔", "error": "❌",
                  "session_summary": "📋"}.get(status, "•")
        delta  = f"+{e['delta']}" if e.get("delta", 0) > 0 else str(e.get("delta",""))
        fname  = e.get("filename", e.get("type", ""))[:30]
        print(f"  {icon} [{e['ts'][:16]}] {status:<10} {fname:<30} {delta}")
    print()

def show_plan():
    print("\n[DREAMER] Observing system...")
    obs = observe_system()
    print(f"\n  SYSTEM STATE")
    print(f"  Oracle: {obs['oracle'].get('score','?')}/100  "
          f"Grade: {obs['oracle'].get('grade','?')}  "
          f"Patch: #{obs['oracle'].get('patch_count','?')}")
    print(f"\n  Endpoints:")
    for name, ep in obs["endpoints"].items():
        icon = "✅" if ep.get("ok") else "❌"
        print(f"    {icon} {name}")
    print(f"\n  Issues flagged ({len(obs['issues'])}):")
    for issue in obs["issues"] or ["None"]:
        print(f"    • {issue}")
    print(f"\n  What Dreamer would target tonight:")
    for issue in obs["issues"][:3]:
        print(f"    → Fix: {issue}")
    if not obs["issues"]:
        print(f"    → System at 100/100 — Dreamer will add new measurement")
        print(f"      dimensions or improve monitoring/alerting capabilities")
    print()

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"

    if not ANTHROPIC_API_KEY and cmd == "run":
        print("❌ ANTHROPIC_API_KEY not set in .env")
        print("   Add: ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    if cmd == "run":
        run_session()
    elif cmd == "status":
        show_status()
    elif cmd == "plan":
        show_plan()
    else:
        print("Usage: python3 omega_dreamer.py [run|status|plan]")
