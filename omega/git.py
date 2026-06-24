#!/usr/bin/env python3
"""
OMEGA AI PRODUCTION BOT
Telegram AI assistant for Omega-Production / omega_bank
Auto-scans, builds awareness, pushes to GitHub, sends notifications.
"""

import os
import sys
import time
import json
import hashlib
import asyncio
import logging
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ParseMode

# ── Load environment ──────────────────────────────────────────────────────────
load_dotenv()

TELEGRAM_TOKEN      = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY")
GITHUB_TOKEN        = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME     = os.getenv("GITHUB_USERNAME", "cipherxsniper")
GITHUB_REPO         = os.getenv("GITHUB_REPO", "omega-fintech")
ALLOWED_USERS       = [int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()]
NOTIFY_CHAT_ID      = os.getenv("NOTIFY_CHAT_ID")

OMEGA_ROOT          = os.getenv("OMEGA_ROOT",      "/Omega-Production")
OMEGA_BANK          = os.getenv("OMEGA_BANK",      "/Omega-Production/omega_bank")
SCAN_INTERVAL       = int(os.getenv("SCAN_INTERVAL_SECONDS", "60"))

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("omega_bot.log"),
    ]
)
log = logging.getLogger("OmegaBot")

# ── Anthropic client ──────────────────────────────────────────────────────────
ai_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── In-memory state ───────────────────────────────────────────────────────────
file_hashes: dict[str, str] = {}
project_snapshot: dict      = {}
conversation_history: dict  = {}   # keyed by chat_id

# ══════════════════════════════════════════════════════════════════════════════
# FILESYSTEM SCANNER
# ══════════════════════════════════════════════════════════════════════════════

IGNORE_PATTERNS = {
    "__pycache__", ".git", "node_modules", ".venv", "venv",
    ".DS_Store", "*.pyc", "*.pyo", "dist", "build", ".env",
}

def should_ignore(path: Path) -> bool:
    for part in path.parts:
        if part in IGNORE_PATTERNS or part.startswith("."):
            return True
    return False

def file_hash(path: Path) -> str:
    try:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""

def scan_directory(root: str) -> dict:
    """Return a structured snapshot of a directory."""
    root_path = Path(root)
    if not root_path.exists():
        return {"error": f"Path not found: {root}"}

    snapshot = {
        "root": str(root_path),
        "scanned_at": datetime.now().isoformat(),
        "total_files": 0,
        "total_dirs": 0,
        "file_types": {},
        "structure": {},
        "key_files": [],
    }

    key_names = {
        "package.json", "requirements.txt", "Pipfile", "pyproject.toml",
        "Makefile", "Dockerfile", "docker-compose.yml", ".env.example",
        "README.md", "main.py", "app.py", "index.js", "server.js",
        "manage.py", "config.py", "settings.py", "schema.sql",
    }

    for path in root_path.rglob("*"):
        if should_ignore(path):
            continue
        rel = str(path.relative_to(root_path))

        if path.is_dir():
            snapshot["total_dirs"] += 1
        elif path.is_file():
            snapshot["total_files"] += 1
            ext = path.suffix.lower() or "no_ext"
            snapshot["file_types"][ext] = snapshot["file_types"].get(ext, 0) + 1
            if path.name in key_names:
                try:
                    content = path.read_text(errors="replace")[:2000]
                except Exception:
                    content = "<binary>"
                snapshot["key_files"].append({
                    "name": path.name,
                    "path": rel,
                    "preview": content,
                })
            # Build tree
            parts = rel.split(os.sep)
            node = snapshot["structure"]
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = "file"

    return snapshot

def full_scan() -> dict:
    """Scan both Omega directories."""
    return {
        "omega_root": scan_directory(OMEGA_ROOT),
        "omega_bank": scan_directory(OMEGA_BANK),
        "timestamp": datetime.now().isoformat(),
    }

def detect_changes() -> list[dict]:
    """Compare current files to stored hashes; return list of changes."""
    changes = []
    for root in [OMEGA_ROOT, OMEGA_BANK]:
        root_path = Path(root)
        if not root_path.exists():
            continue
        for path in root_path.rglob("*"):
            if should_ignore(path) or not path.is_file():
                continue
            key = str(path)
            current = file_hash(path)
            prev = file_hashes.get(key)
            if prev is None:
                changes.append({"type": "added", "path": key})
            elif prev != current:
                changes.append({"type": "modified", "path": key})
            file_hashes[key] = current

    # Detect deletions
    existing = set()
    for root in [OMEGA_ROOT, OMEGA_BANK]:
        for path in Path(root).rglob("*") if Path(root).exists() else []:
            if not should_ignore(path) and path.is_file():
                existing.add(str(path))
    for key in list(file_hashes):
        if key not in existing:
            changes.append({"type": "deleted", "path": key})
            del file_hashes[key]

    return changes

# ══════════════════════════════════════════════════════════════════════════════
# GITHUB AUTO-PUSH
# ══════════════════════════════════════════════════════════════════════════════

def run_git(args: list[str], cwd: str) -> tuple[bool, str]:
    """Run a git command; return (success, output)."""
    env = os.environ.copy()
    env["GIT_ASKPASS"] = "echo"
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd, capture_output=True, text=True, env=env, timeout=30
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, "Git command timed out"
    except Exception as e:
        return False, str(e)

def ensure_git_remote(cwd: str) -> bool:
    """Make sure the remote 'origin' points to the correct repo."""
    remote_url = (
        f"https://{GITHUB_TOKEN}@github.com/"
        f"{GITHUB_USERNAME}/{GITHUB_REPO}.git"
    )
    ok, out = run_git(["remote", "get-url", "origin"], cwd)
    if not ok:
        run_git(["remote", "add", "origin", remote_url], cwd)
    else:
        run_git(["remote", "set-url", "origin", remote_url], cwd)
    return True

def git_push(changes: list[dict], cwd: str) -> tuple[bool, str]:
    """Stage → commit → push changed files."""
    if not Path(cwd).exists():
        return False, f"Directory not found: {cwd}"

    # Init if not a repo
    if not (Path(cwd) / ".git").exists():
        run_git(["init"], cwd)
        run_git(["checkout", "-b", "main"], cwd)

    ensure_git_remote(cwd)
    run_git(["config", "user.email", "omega-bot@production.local"], cwd)
    run_git(["config", "user.name", "Omega AI Bot"], cwd)

    # Stage everything
    ok, out = run_git(["add", "-A"], cwd)
    if not ok:
        return False, f"git add failed: {out}"

    # Check if there's actually something to commit
    ok, status = run_git(["status", "--porcelain"], cwd)
    if not status.strip():
        return True, "Nothing new to commit."

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    changed_names = [Path(c["path"]).name for c in changes[:5]]
    summary = ", ".join(changed_names) if changed_names else "auto-sync"
    msg = f"[OmegaBot] {timestamp} — {summary}"

    ok, out = run_git(["commit", "-m", msg], cwd)
    if not ok:
        return False, f"git commit failed: {out}"

    ok, out = run_git(["push", "-u", "origin", "main", "--force-with-lease"], cwd)
    if not ok:
        # Try force push as fallback
        ok, out = run_git(["push", "-u", "origin", "main", "--force"], cwd)
    return ok, out

# ══════════════════════════════════════════════════════════════════════════════
# AI BRAIN
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are OMEGA, an elite AI production assistant embedded directly
into a fintech development environment. You have deep awareness of two codebases:

1. /Omega-Production  — the main production monorepo
2. /Omega-Production/omega_bank — the banking/fintech core

Your role:
- Answer questions about the codebase with precision and context
- Suggest improvements, spot bugs, recommend architecture decisions
- Track file changes and summarise what's happening in the project
- Help plan features, debug issues, and maintain production quality
- Auto-push changes to GitHub (omega-fintech repo, cipherxsniper)
- Send proactive notifications about important changes

Tone: Direct, technical, expert-level. You are a senior engineer and architect.
Never be vague. Always give actionable output.

When you receive a project snapshot, analyse it deeply:
- Identify the tech stack and architecture
- Spot incomplete features or potential issues
- Understand what's being built toward
- Remember context across the conversation

You have access to real file change events and can trigger git operations."""

def build_context_message(snapshot: dict) -> str:
    """Build a concise project context string for the AI."""
    lines = ["=== OMEGA PROJECT SNAPSHOT ==="]
    for key, data in snapshot.items():
        if key == "timestamp":
            lines.append(f"Scanned: {data}")
            continue
        if isinstance(data, dict) and "error" not in data:
            lines.append(f"\n[{key.upper()}] {data.get('root', '')}")
            lines.append(f"  Files: {data.get('total_files', 0)} | Dirs: {data.get('total_dirs', 0)}")
            types = data.get("file_types", {})
            top_types = sorted(types.items(), key=lambda x: -x[1])[:8]
            lines.append(f"  Types: {', '.join(f'{k}({v})' for k,v in top_types)}")
            for kf in data.get("key_files", [])[:4]:
                lines.append(f"\n  --- {kf['name']} ({kf['path']}) ---")
                lines.append(f"  {kf['preview'][:500]}")
    return "\n".join(lines)

async def ask_ai(chat_id: int, user_message: str, snapshot: dict = None) -> str:
    """Send message to Claude with full conversation history."""
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    content = user_message
    if snapshot:
        content = build_context_message(snapshot) + "\n\n" + user_message

    conversation_history[chat_id].append({"role": "user", "content": content})

    # Keep last 20 turns to stay within context limits
    history = conversation_history[chat_id][-20:]

    try:
        response = ai_client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=history,
        )
        reply = response.content[0].text
        conversation_history[chat_id].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        log.error(f"AI error: {e}")
        return f"⚠️ AI error: {e}"

# ══════════════════════════════════════════════════════════════════════════════
# TELEGRAM HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

def is_authorized(update: Update) -> bool:
    if not ALLOWED_USERS:
        return True
    return update.effective_user.id in ALLOWED_USERS

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    keyboard = [
        [InlineKeyboardButton("📂 Scan Project", callback_data="scan"),
         InlineKeyboardButton("📊 Status", callback_data="status")],
        [InlineKeyboardButton("🚀 Push to GitHub", callback_data="push"),
         InlineKeyboardButton("🧠 AI Analysis", callback_data="analyze")],
        [InlineKeyboardButton("📜 Recent Changes", callback_data="changes"),
         InlineKeyboardButton("🗂️ File Tree", callback_data="tree")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔥 *OMEGA AI PRODUCTION BOT* 🔥\n\n"
        "I'm watching `/Omega-Production` and `/Omega-Production/omega_bank`.\n"
        "Auto-pushing to `cipherxsniper/omega-fintech` on GitHub.\n\n"
        "Ask me anything about the codebase, or use the menu:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=markup,
    )

async def cmd_scan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    msg = await update.message.reply_text("🔍 Scanning Omega directories...")
    global project_snapshot
    project_snapshot = full_scan()
    root_data = project_snapshot.get("omega_root", {})
    bank_data = project_snapshot.get("omega_bank", {})

    text = (
        f"✅ *Scan Complete* — {datetime.now().strftime('%H:%M:%S')}\n\n"
        f"📁 *Omega Root:* {root_data.get('total_files', 'N/A')} files, "
        f"{root_data.get('total_dirs', 'N/A')} dirs\n"
        f"🏦 *Omega Bank:* {bank_data.get('total_files', 'N/A')} files, "
        f"{bank_data.get('total_dirs', 'N/A')} dirs\n\n"
        f"Use *AI Analysis* to get a deep breakdown."
    )
    await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)

async def cmd_push(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    msg = await update.message.reply_text("🚀 Pushing to GitHub...")
    changes = detect_changes()

    # Push both directories
    results = []
    for directory in [OMEGA_ROOT, OMEGA_BANK]:
        if Path(directory).exists():
            ok, out = git_push(changes, directory)
            label = Path(directory).name
            results.append(f"{'✅' if ok else '❌'} *{label}*: `{out[:200]}`")

    text = "🚀 *GitHub Push Results*\n\n" + "\n\n".join(results)
    await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    changes = detect_changes()
    status_lines = [
        f"🟢 *OMEGA BOT ONLINE*",
        f"⏱ Scan interval: {SCAN_INTERVAL}s",
        f"📡 Watching: `{OMEGA_ROOT}` + `{OMEGA_BANK}`",
        f"🔗 Repo: `{GITHUB_USERNAME}/{GITHUB_REPO}`",
        f"📝 Tracked files: `{len(file_hashes)}`",
        f"🔄 Pending changes: `{len(changes)}`",
        f"💬 Active conversations: `{len(conversation_history)}`",
    ]
    await update.message.reply_text(
        "\n".join(status_lines), parse_mode=ParseMode.MARKDOWN
    )

async def cmd_analyze(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    msg = await update.message.reply_text("🧠 Running AI analysis...")
    global project_snapshot
    if not project_snapshot:
        project_snapshot = full_scan()
    reply = await ask_ai(
        update.effective_chat.id,
        "Analyse this project deeply. What is being built? What's the tech stack? "
        "What's incomplete? What are the risks? Give me a structured production briefing.",
        project_snapshot,
    )
    # Split long messages
    if len(reply) > 4000:
        for chunk in [reply[i:i+4000] for i in range(0, len(reply), 4000)]:
            await update.message.reply_text(chunk)
    else:
        await msg.edit_text(reply)

async def cmd_tree(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    global project_snapshot
    if not project_snapshot:
        project_snapshot = full_scan()

    def render_tree(node: dict, indent: int = 0) -> str:
        lines = []
        for name, val in sorted(node.items())[:40]:
            prefix = "  " * indent + ("📄 " if val == "file" else "📁 ")
            lines.append(f"{prefix}{name}")
            if isinstance(val, dict):
                lines.extend(render_tree(val, indent + 1).split("\n"))
        return "\n".join(lines)

    tree_root = render_tree(project_snapshot.get("omega_root", {}).get("structure", {}))
    tree_bank = render_tree(project_snapshot.get("omega_bank", {}).get("structure", {}))

    text = f"📂 *Omega Root Tree:*\n```\n{tree_root[:1500]}\n```\n\n🏦 *Omega Bank Tree:*\n```\n{tree_bank[:1500]}\n```"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    user_text = update.message.text
    await ctx.bot.send_chat_action(update.effective_chat.id, "typing")

    global project_snapshot
    if not project_snapshot:
        project_snapshot = full_scan()

    reply = await ask_ai(update.effective_chat.id, user_text, project_snapshot)

    if len(reply) > 4000:
        for chunk in [reply[i:i+4000] for i in range(0, len(reply), 4000)]:
            await update.message.reply_text(chunk)
    else:
        await update.message.reply_text(reply)

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    fake_update = update
    if data == "scan":
        await cmd_scan(fake_update, ctx)
    elif data == "status":
        await cmd_status(fake_update, ctx)
    elif data == "push":
        await cmd_push(fake_update, ctx)
    elif data == "analyze":
        await cmd_analyze(fake_update, ctx)
    elif data == "changes":
        changes = detect_changes()
        if not changes:
            await query.message.reply_text("✅ No pending changes detected.")
        else:
            lines = [f"{'🆕' if c['type']=='added' else '✏️' if c['type']=='modified' else '🗑️'} `{Path(c['path']).name}`" for c in changes[:20]]
            await query.message.reply_text(
                f"📋 *{len(changes)} change(s) detected:*\n" + "\n".join(lines),
                parse_mode=ParseMode.MARKDOWN,
            )
    elif data == "tree":
        await cmd_tree(fake_update, ctx)

# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND WATCHER (file monitor + auto-push + notifications)
# ══════════════════════════════════════════════════════════════════════════════

async def background_watcher(app: Application):
    """Continuously watches for file changes, auto-pushes, and notifies."""
    log.info("Background watcher started.")
    # Seed hashes silently on first run
    detect_changes()

    while True:
        await asyncio.sleep(SCAN_INTERVAL)
        try:
            changes = detect_changes()
            if not changes:
                continue

            log.info(f"Detected {len(changes)} change(s) — pushing to GitHub")

            # Auto-push
            push_results = []
            for directory in [OMEGA_ROOT, OMEGA_BANK]:
                if Path(directory).exists():
                    ok, out = git_push(changes, directory)
                    push_results.append((Path(directory).name, ok, out))

            # Notify
            if NOTIFY_CHAT_ID:
                added   = [c for c in changes if c["type"] == "added"]
                modified= [c for c in changes if c["type"] == "modified"]
                deleted = [c for c in changes if c["type"] == "deleted"]

                lines = [f"🔔 *Omega Production — {len(changes)} change(s)*\n"]
                if added:
                    lines.append(f"🆕 Added ({len(added)}): " + ", ".join(f"`{Path(c['path']).name}`" for c in added[:5]))
                if modified:
                    lines.append(f"✏️ Modified ({len(modified)}): " + ", ".join(f"`{Path(c['path']).name}`" for c in modified[:5]))
                if deleted:
                    lines.append(f"🗑️ Deleted ({len(deleted)}): " + ", ".join(f"`{Path(c['path']).name}`" for c in deleted[:5]))

                for name, ok, out in push_results:
                    lines.append(f"\n{'✅' if ok else '❌'} GitHub push `{name}`: `{out[:100]}`")

                await app.bot.send_message(
                    chat_id=NOTIFY_CHAT_ID,
                    text="\n".join(lines),
                    parse_mode=ParseMode.MARKDOWN,
                )

        except Exception as e:
            log.error(f"Watcher error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not TELEGRAM_TOKEN:
        log.error("TELEGRAM_TOKEN not set in .env")
        sys.exit(1)
    if not ANTHROPIC_API_KEY:
        log.error("ANTHROPIC_API_KEY not set in .env")
        sys.exit(1)

    log.info("🔥 Starting Omega AI Production Bot...")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("scan",    cmd_scan))
    app.add_handler(CommandHandler("push",    cmd_push))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("analyze", cmd_analyze))
    app.add_handler(CommandHandler("tree",    cmd_tree))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start background watcher as async task
    async def post_init(app: Application):
        asyncio.create_task(background_watcher(app))

    app.post_init = post_init

    log.info(f"Watching: {OMEGA_ROOT}  |  {OMEGA_BANK}")
    log.info(f"Pushing to: github.com/{GITHUB_USERNAME}/{GITHUB_REPO}")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
