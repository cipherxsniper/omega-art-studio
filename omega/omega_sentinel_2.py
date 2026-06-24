#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  OMEGA SENTINEL — Production Script Intelligence System      ║
║  Watches omega_v10.py integrity after every patch            ║
║                                                              ║
║  Commands:                                                   ║
║    python3 omega_sentinel.py scan     — full button audit    ║
║    python3 omega_sentinel.py syntax   — syntax + AST check   ║
║    python3 omega_sentinel.py drift    — detect logic changes  ║
║    python3 omega_sentinel.py snapshot — save current hashes  ║
║    python3 omega_sentinel.py watch    — daemon mode (60s)    ║
║    python3 omega_sentinel.py all      — run everything       ║
╚══════════════════════════════════════════════════════════════╝
"""

import re, sys, ast, json, time, hashlib, subprocess
from pathlib import Path
from datetime import datetime

SCRIPT  = Path("/data/data/com.termux/files/home/omega_v10.py")
SNAP    = Path("/data/data/com.termux/files/home/omega_sentinel_snapshot.json")
ENV     = Path("/data/data/com.termux/files/home/.env")
LOGFILE = Path("/data/data/com.termux/files/home/omega_runtime/logs/sentinel.log")

# ── Telegram push (reads from .env) ───────────────────────────
def _tg_alert(msg: str):
    try:
        import urllib.request, urllib.parse, json as _j, os
        token   = None
        chat_id = None
        for line in ENV.read_text().splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip()
            if line.startswith("TELEGRAM_CHAT_ID="):
                chat_id = line.split("=", 1)[1].strip()
        if not token or not chat_id:
            return
        payload = _j.dumps({"chat_id": chat_id, "text": f"🛡 SENTINEL\n\n{msg}"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=8)
    except Exception:
        pass

def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        LOGFILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOGFILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════
# 1. SYNTAX CHECK
# ══════════════════════════════════════════════════════════════
def check_syntax() -> bool:
    _log("── SYNTAX CHECK ─────────────────────────────")
    src = SCRIPT.read_text()

    # py_compile
    try:
        import py_compile, tempfile, shutil
        tmp = Path(tempfile.mktemp(suffix=".py"))
        shutil.copy(SCRIPT, tmp)
        py_compile.compile(str(tmp), doraise=True)
        tmp.unlink()
        _log("  ✅ py_compile — PASS")
    except Exception as e:
        _log(f"  ❌ py_compile — FAIL: {e}")
        return False

    # AST parse
    try:
        tree = ast.parse(src)
        _log("  ✅ AST parse — PASS")
    except SyntaxError as e:
        _log(f"  ❌ AST parse — FAIL: line {e.lineno}: {e.msg}")
        return False

    # Indentation scan (common heredoc corruption)
    indent_errors = []
    for i, line in enumerate(src.splitlines(), 1):
        if line and line[0] == " ":
            spaces = len(line) - len(line.lstrip(" "))
            if spaces % 4 != 0 and not line.strip().startswith("#"):
                indent_errors.append(f"    line {i}: {spaces} spaces — '{line.strip()[:50]}'")
    if indent_errors[:5]:
        _log(f"  ⚠️  Indent anomalies ({len(indent_errors)} total):")
        for e in indent_errors[:5]:
            _log(e)
    else:
        _log("  ✅ Indentation — PASS")

    # Duplicate function definitions
    funcs = re.findall(r"^(?:async )?def (\w+)\(", src, re.MULTILINE)
    seen, dupes = set(), set()
    for f in funcs:
        if f in seen:
            dupes.add(f)
        seen.add(f)
    if dupes:
        _log(f"  ⚠️  Duplicate functions: {sorted(dupes)}")
    else:
        _log("  ✅ No duplicate function definitions")

    return True

# ══════════════════════════════════════════════════════════════
# 2. BUTTON AUDIT — every callback_data has a handler
# ══════════════════════════════════════════════════════════════
def scan_buttons() -> bool:
    _log("── BUTTON AUDIT ─────────────────────────────")
    src = SCRIPT.read_text()

    # All callback_data values defined in menus
    defined = set(re.findall(r'callback_data=["\']([^"\']+)["\']', src))

    # All handled data values (elif data == or if data ==)
    handled = set(re.findall(r'(?:if|elif)\s+data\s*(?:==|in)\s*["\(]([^"\')\n]+)["\)]', src))
    # Also catch: data in ("x", "y")
    multi   = re.findall(r'data\s+in\s+\(([^)]+)\)', src)
    for group in multi:
        for item in re.findall(r'["\']([^"\']+)["\']', group):
            handled.add(item)

    # Registered patterns in build_telegram_app
    patterns = re.findall(r'pattern=["\']([^"\']+)["\']', src)

    _log(f"  Buttons defined:  {len(defined)}")
    _log(f"  Handlers found:   {len(handled)}")
    _log(f"  Patterns:         {patterns}")

    all_ok = True
    orphaned = []
    for cb in sorted(defined):
        # Check if handled directly OR covered by a pattern
        direct = cb in handled
        covered = any(
            re.search(p.replace("^", "").replace("(", "").replace(")", ""), cb)
            for p in patterns
        )
        if direct or covered:
            _log(f"  ✅ {cb}")
        else:
            _log(f"  ❌ {cb} — NO HANDLER")
            orphaned.append(cb)
            all_ok = False

    if orphaned:
        msg = f"❌ {len(orphaned)} unhandled buttons:\n" + "\n".join(f"  • {b}" for b in orphaned)
        _log(f"\n  ALERT: {msg}")
        _tg_alert(msg)
    else:
        _log("\n  ✅ All buttons have handlers")

    return all_ok

# ══════════════════════════════════════════════════════════════
# 3. DRIFT DETECTION — hash every function, compare to snapshot
# ══════════════════════════════════════════════════════════════
def _extract_functions(src: str) -> dict:
    """Extract every function body and hash it."""
    hashes = {}
    try:
        tree = ast.parse(src)
        lines = src.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno - 1
                end   = node.end_lineno
                body  = "\n".join(lines[start:end])
                hashes[node.name] = {
                    "hash": hashlib.sha256(body.encode()).hexdigest()[:16],
                    "line": node.lineno,
                    "size": end - start
                }
    except Exception:
        pass
    return hashes

def save_snapshot():
    src     = SCRIPT.read_text()
    funcs   = _extract_functions(src)
    snap    = {
        "ts":        datetime.now().isoformat(),
        "file_hash": hashlib.sha256(src.encode()).hexdigest()[:16],
        "functions": funcs
    }
    SNAP.write_text(json.dumps(snap, indent=2))
    _log(f"── SNAPSHOT SAVED ───────────────────────────")
    _log(f"  {len(funcs)} functions hashed → {SNAP}")

def check_drift() -> bool:
    _log("── DRIFT DETECTION ──────────────────────────")
    if not SNAP.exists():
        _log("  ⚠️  No snapshot found — run: python3 omega_sentinel.py snapshot")
        return True

    snap    = json.loads(SNAP.read_text())
    src     = SCRIPT.read_text()
    current = _extract_functions(src)
    old     = snap.get("functions", {})

    drifted  = []
    added    = []
    removed  = []

    for name, info in current.items():
        if name not in old:
            added.append(name)
        elif info["hash"] != old[name]["hash"]:
            drifted.append(
                f"  ⚠️  {name}() — hash changed "
                f"({old[name]['hash']} → {info['hash']}) "
                f"line {info['line']}"
            )

    for name in old:
        if name not in current:
            removed.append(name)

    all_ok = True
    if drifted:
        _log(f"  ❌ {len(drifted)} functions modified unexpectedly:")
        for d in drifted:
            _log(d)
        msg = f"⚠️ DRIFT DETECTED\n{len(drifted)} functions changed:\n" + "\n".join(
            d.strip() for d in drifted
        )
        _tg_alert(msg)
        all_ok = False
    else:
        _log("  ✅ No drift — all existing functions unchanged")

    if added:
        _log(f"  ➕ New functions added ({len(added)}): {', '.join(added[:10])}")
    if removed:
        _log(f"  ➖ Functions removed ({len(removed)}): {', '.join(removed[:10])}")
        all_ok = False

    return all_ok

# ══════════════════════════════════════════════════════════════
# 4. MEXC LIVE CHECK
# ══════════════════════════════════════════════════════════════
def check_mexc():
    _log("── MEXC LIVE PRICE CHECK ────────────────────")
    try:
        import urllib.request, json as _j
        for sym in ["XRPUSDT", "BTCUSDT", "ETHUSDT"]:
            url = f"https://api.mexc.com/api/v3/ticker/price?symbol={sym}"
            with urllib.request.urlopen(url, timeout=8) as r:
                price = float(_j.loads(r.read())["price"])
            _log(f"  ✅ {sym}: ${price:,.4f}")
    except Exception as e:
        _log(f"  ❌ MEXC price check failed: {e}")

# ══════════════════════════════════════════════════════════════
# 5. OMEGA PROCESS CHECK
# ══════════════════════════════════════════════════════════════
def check_process():
    _log("── PROCESS CHECK ────────────────────────────")
    result = subprocess.run(["pgrep", "-f", "omega_v10.py"], capture_output=True, text=True)
    if result.stdout.strip():
        _log(f"  ✅ omega_v10.py running — PID {result.stdout.strip()}")
    else:
        _log("  ❌ omega_v10.py NOT RUNNING")
        _tg_alert("❌ omega_v10.py is DOWN — guardian should restart in 30s")

# ══════════════════════════════════════════════════════════════
# 6. FULL REPORT
# ══════════════════════════════════════════════════════════════
def run_all():
    _log("=" * 54)
    _log("  OMEGA SENTINEL — FULL REPORT")
    _log(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    _log("=" * 54)
    ok_syntax  = check_syntax()
    _log("")
    ok_buttons = scan_buttons()
    _log("")
    ok_drift   = check_drift()
    _log("")
    check_mexc()
    _log("")
    check_process()
    _log("")
    _log("=" * 54)
    status = "✅ ALL CLEAR" if (ok_syntax and ok_buttons and ok_drift) else "❌ ISSUES FOUND — see above"
    _log(f"  {status}")
    _log("=" * 54)
    return ok_syntax and ok_buttons and ok_drift

# ══════════════════════════════════════════════════════════════
# 7. WATCH DAEMON
# ══════════════════════════════════════════════════════════════
def watch_daemon(interval: int = 60):
    _log(f"SENTINEL DAEMON — watching every {interval}s. Ctrl+C to stop.")
    last_file_hash = ""
    while True:
        try:
            src  = SCRIPT.read_text()
            fhsh = hashlib.sha256(src.encode()).hexdigest()[:16]
            if fhsh != last_file_hash:
                _log(f"\n  📄 Script changed (hash {fhsh}) — running checks...")
                run_all()
                last_file_hash = fhsh
            else:
                check_process()
            time.sleep(interval)
        except KeyboardInterrupt:
            _log("Sentinel stopped.")
            break
        except Exception as e:
            _log(f"Sentinel error: {e}")
            time.sleep(interval)

# ══════════════════════════════════════════════════════════════
# ENTRYPOINT
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"

    if cmd == "syntax":
        check_syntax()
    elif cmd == "scan":
        scan_buttons()
    elif cmd == "drift":
        check_drift()
    elif cmd == "snapshot":
        save_snapshot()
    elif cmd == "mexc":
        check_mexc()
    elif cmd == "process":
        check_process()
    elif cmd == "watch":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        watch_daemon(interval)
    elif cmd == "all":
        ok = run_all()
        sys.exit(0 if ok else 1)
    else:
        print("Usage: python3 omega_sentinel.py [scan|syntax|drift|snapshot|watch|mexc|all]")
