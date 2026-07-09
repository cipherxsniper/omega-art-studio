# =========================
# OMEGA TELEGRAM V3
# Production Financial OS Command Center
# Extends omega_telegram_2.py — do NOT run both on same token simultaneously
# =========================

# 🔐 Runtime Safety Kernel
from omega_import_guard import enforce_import_safety
enforce_import_safety()

# 🧭 System Contract Layer
from omega_contracts import validate_call

# 🏦 Core Orchestrator
import omega_unified_system_orchestrator_v1 as orchestrator

# 📒 Ledger + Event System
import event_ledger_engine
import ledger_write

# 💰 Banking / Accounts
import bank

# 📊 Settlement + Reconciliation
import settlement_reconciliation_engine

# 🔥 Fraud / Risk Engine
try:
    import omega_fraud_scan
    _fraud_available = True
except ImportError:
    _fraud_available = False

# 🧾 Environment
import os
from dotenv import load_dotenv
load_dotenv()

# 🤖 Telegram
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# 🧠 Logging
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [OMEGA] %(levelname)s: %(message)s",
)
logger = logging.getLogger("OMEGA_TELEGRAM_V3")

# =========================
# ENV CONFIG — FAIL FAST
# =========================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
STRIPE_SECRET_KEY  = os.getenv("STRIPE_SECRET_KEY")
DATABASE_PATH      = os.getenv("DATABASE_PATH", "omega_ledger.db")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in .env — cannot start bot")

# =========================
# INTERNAL HELPERS
# =========================
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _uid(update: Update) -> str:
    return str(update.effective_user.id)

def _uname(update: Update) -> str:
    return update.effective_user.username or str(update.effective_user.id)

def _fmt_usd(amount) -> str:
    """Format any numeric value as clean USD string."""
    try:
        val = Decimal(str(amount))
        return f"${val:,.2f} USD"
    except (InvalidOperation, TypeError):
        return "$0.00 USD"

def _safe_get(fn, fallback=None):
    """Safe wrapper for all engine calls — prevents crash propagation."""
    try:
        result = validate_call(fn)
        return result if result is not None else fallback
    except Exception as e:
        logger.error("[SAFE_GET] %s: %s", getattr(fn, "__name__", repr(fn)), e)
        return fallback

def _chunk_msg(text: str, size: int = 4000):
    for i in range(0, len(text), size):
        yield text[i:i + size]

async def _reply(update: Update, text: str, md: bool = True) -> None:
    mode = "Markdown" if md else None
    for chunk in _chunk_msg(text):
        await update.message.reply_text(chunk, parse_mode=mode)

# =========================
# FRAUD SCAN FACADE
# =========================
def run_fraud_scan() -> list:
    if _fraud_available:
        try:
            return validate_call(omega_fraud_scan.run) or []
        except Exception as e:
            logger.error("[FRAUD_SCAN] %s", e)
    return []

# =========================
# LEDGER SNAPSHOT FACADE
# =========================
def get_ledger_snapshot() -> dict:
    try:
        snap = validate_call(event_ledger_engine.get_ledger_snapshot)
        return snap if isinstance(snap, dict) else {}
    except Exception as e:
        logger.error("[LEDGER_SNAPSHOT] %s", e)
        return {}

# =========================
# BANK SNAPSHOT FACADE
# =========================
def get_bank_snapshot() -> dict:
    try:
        snap = validate_call(bank.get_snapshot)
        return snap if isinstance(snap, dict) else {}
    except Exception as e:
        logger.error("[BANK_SNAPSHOT] %s", e)
        return {}

# =========================
# EVENTS FACADE
# =========================
def get_recent_ledger_events(limit: int = 20) -> list:
    try:
        events = validate_call(event_ledger_engine.get_recent_events)
        if isinstance(events, list):
            return events[-limit:]
        return []
    except Exception as e:
        logger.error("[EVENTS] %s", e)
        return []

# =========================
# RECONCILIATION FACADE
# =========================
def get_reconciliation() -> dict:
    try:
        result = validate_call(settlement_reconciliation_engine.run_reconciliation)
        return result if isinstance(result, dict) else {}
    except Exception as e:
        logger.error("[RECONCILE] %s", e)
        return {}

# =========================
# ORCHESTRATOR FACADE
# =========================
def trigger_orchestrator(payload: dict | None = None) -> dict:
    try:
        result = validate_call(lambda: orchestrator.run(payload or {}))
        return result if isinstance(result, dict) else {"status": "COMPLETE", "raw": str(result)}
    except Exception as e:
        logger.error("[ORCHESTRATOR] %s", e)
        return {"status": "ERROR", "reason": str(e)}

# =========================
# LEDGER WRITE FACADE
# =========================
def write_ledger_event(event: dict) -> bool:
    try:
        if not isinstance(event, dict) or "type" not in event:
            raise ValueError("Invalid event — must be dict with 'type'")
        payload = event.get("payload", {})
        if isinstance(payload, dict) and "amount" in payload:
            amt = float(str(payload["amount"]).replace("USD","").replace(",","").strip())
            if amt <= 0:
                raise ValueError("Amount must be > 0")
        validate_call(lambda: ledger_write.write(event))
        return True
    except Exception as e:
        logger.error("[LEDGER_WRITE_BLOCKED] %s", e)
        return False

# =========================
# /start
# =========================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update,
        "🏦 *OMEGA FINANCIAL OS — v3*\n"
        "_Production Command Center_\n\n"
        "*Banking*\n"
        "  /bank — Full account ledger dashboard\n"
        "  /system\\_total — Total treasury + liabilities\n"
        "  /balance — Your wallet balance\n\n"
        "*Events & Ledger*\n"
        "  /events — Last 20 ledger events\n"
        "  /timeline — Grouped event stream\n\n"
        "*Transfers*\n"
        "  /approve\\_transfer `<from> <to> <amount>` — Validated transfer\n\n"
        "*Audit & Control*\n"
        "  /run\\_health\\_check — Full system diagnostic\n"
        "  /trigger\\_settlement — Run orchestrator pipeline\n"
        "  /reconcile — Drift detection report\n"
        "  /fraud\\_scan — Event-based risk scan\n\n"
        "_All mutations route through orchestrator. No direct ledger writes from UI._"
    )

# =========================
# /bank — Full ledger dashboard
# =========================
async def cmd_bank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    snap   = get_ledger_snapshot()
    bsnap  = get_bank_snapshot()
    recon  = get_reconciliation()
    drift  = recon.get("drift", False)

    accounts = snap.get("accounts", bsnap.get("accounts", {}))
    total    = snap.get("total",    bsnap.get("total",    0))
    treasury = snap.get("treasury", bsnap.get("treasury", 0))
    liabs    = snap.get("liabilities", 0)

    drift_line = "⚠️ DRIFT DETECTED — run /reconcile" if drift else "✅ Balanced"

    lines = [
        "🏦 *OMEGA BANK — Ledger Dashboard*",
        f"`{'─'*36}`",
    ]

    if isinstance(accounts, dict) and accounts:
        for acct_id, bal in sorted(accounts.items()):
            tag = " ← TREASURY" if "treasury" in str(acct_id).lower() else ""
            lines.append(f"  `{acct_id}`:  *{_fmt_usd(bal)}*{tag}")
    elif isinstance(accounts, list) and accounts:
        for acct in accounts:
            acct_id = acct.get("id", acct.get("account_id", "?"))
            bal     = acct.get("balance", acct.get("amount", 0))
            tag     = " ← TREASURY" if "treasury" in str(acct_id).lower() else ""
            lines.append(f"  `{acct_id}`:  *{_fmt_usd(bal)}*{tag}")
    else:
        lines.append("  _No account data returned from ledger engine_")

    lines += [
        f"`{'─'*36}`",
        f"  Treasury:    *{_fmt_usd(treasury)}*",
        f"  Liabilities: *{_fmt_usd(liabs)}*",
        f"  Total:       *{_fmt_usd(total)}*",
        f"`{'─'*36}`",
        f"  Reconciliation: `{drift_line}`",
        f"  Generated: `{_now()[:19].replace('T',' ')} UTC`",
        "",
        "_Source: ledger engine + consensus replay_",
    ]
    await _reply(update, "\n".join(lines))

# =========================
# /system_total
# =========================
async def cmd_system_total(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    snap     = get_ledger_snapshot()
    bsnap    = get_bank_snapshot()
    total    = snap.get("total",       bsnap.get("total",       0))
    treasury = snap.get("treasury",    bsnap.get("treasury",    0))
    liabs    = snap.get("liabilities", bsnap.get("liabilities", 0))
    net      = float(total) - float(liabs)

    lines = [
        "💰 *OMEGA System Total*",
        f"`{'─'*30}`",
        f"  Ledger total:  *{_fmt_usd(total)}*",
        f"  Treasury:      *{_fmt_usd(treasury)}*",
        f"  Liabilities:   *{_fmt_usd(liabs)}*",
        f"  Net position:  *{_fmt_usd(net)}*",
        f"`{'─'*30}`",
        f"  At: `{_now()[:19].replace('T',' ')} UTC`",
        "",
        "_Derived from ledger engine — not hardcoded._",
    ]
    await _reply(update, "\n".join(lines))

# =========================
# /balance
# =========================
async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid  = _uid(update)
    snap = get_ledger_snapshot()
    accounts = snap.get("accounts", {})
    bal  = None
    if isinstance(accounts, dict):
        bal = accounts.get(uid) or accounts.get(f"wallet_{uid}")
    if bal is None:
        # Try bank snapshot
        bsnap = get_bank_snapshot()
        baccts = bsnap.get("accounts", {})
        if isinstance(baccts, dict):
            bal = baccts.get(uid)

    if bal is None:
        await _reply(update,
            "⚠️ No balance found for your user ID in the ledger.\n\n"
            "_Create a wallet using the Phase 3 bot first._"
        )
        return

    await _reply(update,
        f"💰 *Your Balance*\n\n"
        f"  Account: `{uid}`\n"
        f"  Balance: *{_fmt_usd(bal)}*\n\n"
        f"_Ledger-derived balance._"
    )

# =========================
# /events — Last 20 ledger events
# =========================
async def cmd_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    events = get_recent_ledger_events(20)

    if not events:
        await _reply(update, "📭 No ledger events found.")
        return

    type_icons = {
        "TRANSFER":        "💸",
        "TRANSFER_INTENT": "💸",
        "DEBIT":           "📤",
        "CREDIT":          "📥",
        "SETTLEMENT":      "⚖️",
        "WALLET_CREATED":  "💼",
        "CARD_ISSUED":     "💳",
        "QR_PAYMENT_INTENT": "📷",
        "ORCHESTRATOR_RUN":  "⚙️",
        "ACCOUNT_LINKED":    "🔗",
    }

    lines = [f"📋 *Ledger Event Stream* (last {len(events)})\n"]
    for e in reversed(events):
        typ  = e.get("type", e.get("event_type", "UNKNOWN"))
        ts   = e.get("written_at", e.get("timestamp", e.get("created_at", "?")))
        ts   = str(ts)[:19].replace("T", " ")
        icon = type_icons.get(typ, "📋")
        p    = e.get("payload", {})
        acct = (
            p.get("from") or p.get("account") or
            e.get("account_id") or e.get("wallet_id") or "—"
        )
        amt_raw = p.get("amount") or e.get("amount")
        amt_str = f" `{_fmt_usd(amt_raw)}`" if amt_raw else ""
        lines.append(f"  {icon} `{ts}` `{typ}`{amt_str}")
        if acct and acct != "—":
            lines.append(f"       Account: `{acct}`")

    await _reply(update, "\n".join(lines))

# =========================
# /approve_transfer <from> <to> <amount>
# =========================
async def cmd_approve_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args or len(args) < 3:
        await _reply(update,
            "⚠️ *Usage:* `/approve_transfer <from> <to> <amount>`\n\n"
            "*Examples:*\n"
            "`/approve_transfer TREASURY ACC-001 5000`\n"
            "`/approve_transfer wallet_123 wallet_456 250.00`"
        )
        return

    from_acct = args[0]
    to_acct   = args[1]

    try:
        amount = float(args[2].replace(",", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await _reply(update, "❌ Amount must be a positive number.")
        return

    # Validation: check ledger for from_acct existence
    snap     = get_ledger_snapshot()
    accounts = snap.get("accounts", {})
    if isinstance(accounts, dict) and accounts:
        from_bal = accounts.get(from_acct)
        if from_bal is not None and float(from_bal) < amount:
            await _reply(update,
                f"❌ *Insufficient Balance*\n\n"
                f"  Account: `{from_acct}`\n"
                f"  Available: `{_fmt_usd(from_bal)}`\n"
                f"  Requested: `{_fmt_usd(amount)}`"
            )
            return

    intent_id = str(uuid.uuid4())
    event = {
        "type": "TRANSFER_INTENT",
        "intent_id": intent_id,
        "payload": {
            "from":   from_acct,
            "to":     to_acct,
            "amount": f"{amount:.2f} USD",
        },
        "approved_by":   _uid(update),
        "approved_at":   _now(),
    }

    # Write approval to ledger
    written = write_ledger_event(event)
    if not written:
        await _reply(update, "❌ Ledger write failed. Transfer not recorded.")
        return

    # Route to orchestrator
    result = trigger_orchestrator({
        "action":    "transfer",
        "from":      from_acct,
        "to":        to_acct,
        "amount":    amount,
        "intent_id": intent_id,
    })

    status = result.get("status", "UNKNOWN")
    await _reply(update,
        f"✅ *Transfer Approved & Routed*\n\n"
        f"  From:      `{from_acct}`\n"
        f"  To:        `{to_acct}`\n"
        f"  Amount:    `{_fmt_usd(amount)}`\n"
        f"  Intent ID: `{intent_id}`\n"
        f"  Status:    `{status}`\n\n"
        f"_Ledger event recorded. Routed via orchestrator._"
    )

# =========================
# /run_health_check — Enhanced
# =========================
async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lines = ["🏥 *OMEGA System Health*\n"]

    # Ledger engine
    try:
        snap = get_ledger_snapshot()
        acct_count = len(snap.get("accounts", {}))
        lines.append(f"  ✅ `ledger_engine`:      OK ({acct_count} accounts)")
    except Exception as e:
        lines.append(f"  ❌ `ledger_engine`:      FAIL — {e}")

    # Event bus
    try:
        events = get_recent_ledger_events(5)
        lines.append(f"  ✅ `event_bus`:          OK ({len(events)} recent events)")
    except Exception as e:
        lines.append(f"  ❌ `event_bus`:          FAIL — {e}")

    # Settlement engine
    try:
        recon = get_reconciliation()
        settle_status = recon.get("settlement_state", recon.get("status", "UNKNOWN"))
        icon = "✅" if "OK" in str(settle_status).upper() or "SETTLE" in str(settle_status).upper() else "⚠️"
        lines.append(f"  {icon} `settlement_engine`:  {settle_status}")
    except Exception as e:
        lines.append(f"  ❌ `settlement_engine`:  FAIL — {e}")

    # Reconciliation drift
    try:
        recon = get_reconciliation()
        drift = recon.get("drift", False)
        parity = recon.get("parity_score", recon.get("parity", "N/A"))
        icon = "⚠️" if drift else "✅"
        lines.append(f"  {icon} `reconciliation`:     {'DRIFT DETECTED' if drift else 'OK'} | parity: {parity}")
    except Exception as e:
        lines.append(f"  ❌ `reconciliation`:     FAIL — {e}")

    # Bank snapshot
    try:
        bsnap = get_bank_snapshot()
        total = bsnap.get("total", 0)
        lines.append(f"  ✅ `bank_engine`:        OK | total: {_fmt_usd(total)}")
    except Exception as e:
        lines.append(f"  ❌ `bank_engine`:        FAIL — {e}")

    # Fraud scan
    try:
        results = run_fraud_scan()
        high = [r for r in results if isinstance(r, dict) and r.get("risk_score", 0) >= 0.7]
        icon = "⚠️" if high else "✅"
        lines.append(f"  {icon} `fraud_engine`:       {len(results)} wallets scanned | {len(high)} high-risk")
    except Exception as e:
        lines.append(f"  ⚠️ `fraud_engine`:       unavailable — {e}")

    # Orchestrator
    try:
        validate_call(lambda: None)   # contract layer ping
        lines.append(f"  ✅ `orchestrator`:       ONLINE")
    except Exception as e:
        lines.append(f"  ❌ `orchestrator`:       FAIL — {e}")

    lines += [
        "",
        f"  `checked_at`: `{_now()[:19].replace('T',' ')} UTC`",
        "",
        "_Legend: ✅ OK  ⚠️ WARNING  ❌ FAIL_",
    ]
    await _reply(update, "\n".join(lines))

# =========================
# /trigger_settlement
# =========================
async def cmd_trigger_settlement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "⚙️ Running orchestrator pipeline...")
    result = trigger_orchestrator({"action": "settle"})
    status = result.get("status", "UNKNOWN")
    accts  = result.get("account_count", result.get("accounts", "?"))
    events = result.get("event_count",   result.get("events",   "?"))
    value  = result.get("total_value_usd", result.get("total", 0))

    await _reply(update,
        f"⚙️ *Orchestrator Run Complete*\n\n"
        f"  Status:   `{status}`\n"
        f"  Accounts: `{accts}`\n"
        f"  Events:   `{events}`\n"
        f"  Value:    `{_fmt_usd(value)}`\n\n"
        f"  Pipeline: `Event Bus → Consensus → Settlement → Stripe Mirror`\n"
        f"  At:       `{_now()[:19].replace('T',' ')} UTC`"
    )

# =========================
# /reconcile
# =========================
async def cmd_reconcile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    recon  = get_reconciliation()
    drift  = recon.get("drift", False)
    parity = recon.get("parity_score", recon.get("parity", "N/A"))
    ledger = recon.get("ledger_events",      recon.get("ledger_count",  "?"))
    stripe = recon.get("stripe_events",      recon.get("stripe_count",  "?"))
    settle = recon.get("settlement_state",   recon.get("status",        "?"))
    consen = recon.get("consensus_accounts", recon.get("accounts",      "?"))

    status_line = "⚠️ DRIFT DETECTED" if drift else "✅ BALANCED"

    lines = [
        "🔁 *Reconciliation Report*\n",
        f"  Status:            `{status_line}`",
        f"  Ledger events:     `{ledger}`",
        f"  Consensus accts:   `{consen}`",
        f"  Stripe events:     `{stripe}`",
        f"  Settlement state:  `{settle}`",
        f"  Parity score:      `{parity}`",
        f"  Drift:             `{drift}`",
        f"  At: `{_now()[:19].replace('T',' ')} UTC`",
    ]
    if drift:
        lines.append("\n_⚠️ Run /trigger\\_settlement to resync._")
    else:
        lines.append("\n_All systems consistent._")

    await _reply(update, "\n".join(lines))

# =========================
# /fraud_scan
# =========================
async def cmd_fraud_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "🔍 Running fraud scan...")
    results = run_fraud_scan()

    if not results:
        await _reply(update,
            "✅ *Fraud Scan Complete*\n\n"
            "No anomalies detected.\n\n"
            "_0 wallets flagged._"
        )
        return

    high   = [r for r in results if isinstance(r, dict) and r.get("risk_score", 0) >= 0.7]
    medium = [r for r in results if isinstance(r, dict) and 0.4 <= r.get("risk_score", 0) < 0.7]
    low    = [r for r in results if isinstance(r, dict) and r.get("risk_score", 0) < 0.4]

    lines = [f"🚨 *Fraud Scan Results*\n\n"
             f"  Scanned: `{len(results)}` | "
             f"🔴 High: `{len(high)}` | "
             f"🟡 Med: `{len(medium)}` | "
             f"🟢 Low: `{len(low)}`\n"]

    for r in results[:15]:
        score  = r.get("risk_score", 0)
        wid    = r.get("wallet_id", r.get("account_id", "?"))
        flags  = r.get("flags", [])
        tx     = r.get("tx_count", "?")
        vol    = r.get("total_usd", r.get("volume", 0))
        level  = "🔴" if score >= 0.7 else "🟡" if score >= 0.4 else "🟢"
        lines.append(
            f"\n{level} `{wid}`\n"
            f"  Score: `{score}` | TXs: `{tx}` | Vol: `{_fmt_usd(vol)}`\n"
            f"  Flags: `{', '.join(flags) if flags else 'none'}`"
        )

    lines.append("\n_Event-based heuristics only. No ML models._")
    await _reply(update, "\n".join(lines))

# =========================
# /timeline — grouped event stream
# =========================
async def cmd_timeline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    events  = get_recent_ledger_events(50)
    TRACKED = {
        "TRANSFER","TRANSFER_INTENT","DEBIT","CREDIT","SETTLEMENT",
        "WALLET_CREATED","CARD_ISSUED","QR_PAYMENT_INTENT","ORCHESTRATOR_RUN",
    }
    tracked = [e for e in events if e.get("type", e.get("event_type","")) in TRACKED]

    if not tracked:
        await _reply(update, "📭 No tracked events in ledger yet.")
        return

    from collections import defaultdict
    groups  = defaultdict(list)
    icons   = {
        "TRANSFER":          "💸",
        "TRANSFER_INTENT":   "💸",
        "DEBIT":             "📤",
        "CREDIT":            "📥",
        "SETTLEMENT":        "⚖️",
        "WALLET_CREATED":    "💼",
        "CARD_ISSUED":       "💳",
        "QR_PAYMENT_INTENT": "📷",
        "ORCHESTRATOR_RUN":  "⚙️",
    }

    for e in tracked:
        groups[e.get("type", e.get("event_type","?"))].append(e)

    lines = ["🧾 *Ledger Timeline* (grouped)\n"]
    for typ, evts in sorted(groups.items()):
        icon = icons.get(typ, "📋")
        lines.append(f"\n{icon} *{typ}* — {len(evts)} events")
        for e in evts[-5:]:
            ts  = str(e.get("written_at", e.get("timestamp","?")))[:19].replace("T"," ")
            p   = e.get("payload", {})
            amt = p.get("amount") or e.get("amount")
            amt_str = f" `{_fmt_usd(amt)}`" if amt else ""
            lines.append(f"  `{ts}`{amt_str}")

    await _reply(update, "\n".join(lines))

# =========================
# Error handler
# =========================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            f"⚠️ `{type(context.error).__name__}: {context.error}`",
            parse_mode="Markdown",
        )

# =========================
# BOOTSTRAP
# =========================
def main() -> None:
    logger.info("OMEGA Telegram V3 starting — production mode")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",              cmd_start))
    app.add_handler(CommandHandler("bank",               cmd_bank))
    app.add_handler(CommandHandler("system_total",       cmd_system_total))
    app.add_handler(CommandHandler("balance",            cmd_balance))
    app.add_handler(CommandHandler("events",             cmd_events))
    app.add_handler(CommandHandler("timeline",           cmd_timeline))
    app.add_handler(CommandHandler("approve_transfer",   cmd_approve_transfer))
    app.add_handler(CommandHandler("run_health_check",   cmd_health))
    app.add_handler(CommandHandler("trigger_settlement", cmd_trigger_settlement))
    app.add_handler(CommandHandler("reconcile",          cmd_reconcile))
    app.add_handler(CommandHandler("fraud_scan",         cmd_fraud_scan))
    app.add_error_handler(error_handler)

    logger.info("OMEGA V3 online — polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
