"""
OMEGA AI FINANCIAL CORE
Telegram Operator Terminal v1 — Self-Contained Edition
All engines run in-process. Zero external module dependencies.
Requires: python-telegram-bot python-dotenv
"""

import os
import json
import uuid
import hashlib
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("OMEGA.Terminal")

# ---------------------------------------------------------------------------
# File paths  (all state is file-backed — no external DB)
# ---------------------------------------------------------------------------
LEDGER_PATH     = Path("omega_ledger.json")
WALLET_PATH     = Path("omega_wallets.json")
CARD_PATH       = Path("omega_cards.json")
SETTLEMENT_PATH = Path("omega_settlement.json")
STRIPE_PATH     = Path("omega_stripe_mirror.json")

_file_lock = threading.Lock()

def _load(path: Path):
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return [] if "ledger" in path.name else {}

def _save(path: Path, data) -> None:
    with _file_lock:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


# ===========================================================================
# ENGINE LAYER  (all in-process)
# ===========================================================================

# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------
class _EventBus:
    def get_recent_events(self, limit: int = 100) -> list:
        events = _load(LEDGER_PATH)
        return events[-limit:] if isinstance(events, list) else []

    def write_event(self, event: dict) -> None:
        events = _load(LEDGER_PATH)
        if not isinstance(events, list):
            events = []
        event.setdefault("event_id", str(uuid.uuid4()))
        event.setdefault("written_at", _now())
        events.append(event)
        _save(LEDGER_PATH, events)

    def get_event_count(self) -> int:
        events = _load(LEDGER_PATH)
        return len(events) if isinstance(events, list) else 0

event_bus = _EventBus()


# ---------------------------------------------------------------------------
# Consensus Engine
# ---------------------------------------------------------------------------
class _ConsensusEngine:
    def replay_balances(self, events: list) -> dict:
        balances = defaultdict(float)
        for e in events:
            t = e.get("type", "")
            p = e.get("payload", {})
            if t == "TRANSFER_APPROVAL":
                src = p.get("from", "")
                dst = p.get("to", "")
                try:
                    amt = float(str(p.get("amount", "0")).replace("USD", "").strip().replace(",", ""))
                except ValueError:
                    amt = 0.0
                if src:
                    balances[src] -= amt
                if dst:
                    balances[dst] += amt
            elif t == "WALLET_CREATED":
                wid = e.get("wallet_id", "")
                if wid and wid not in balances:
                    balances[wid] = float(e.get("balance", 0.0))
        return dict(balances)

    def build_consensus_snapshot(self, events: list, balances: dict) -> dict:
        return {
            "snapshot_at":     _now(),
            "event_count":     len(events),
            "account_count":   len(balances),
            "total_value_usd": round(sum(v for v in balances.values() if v > 0), 2),
        }

consensus = _ConsensusEngine()


# ---------------------------------------------------------------------------
# Settlement Engine
# ---------------------------------------------------------------------------
class _SettlementEngine:
    def run_settlement(self) -> dict:
        events   = event_bus.get_recent_events()
        balances = consensus.replay_balances(events)
        snap = {
            "settled_at":    _now(),
            "accounts":      len(balances),
            "total_settled": round(sum(v for v in balances.values() if v > 0), 2),
            "status":        "SETTLED",
        }
        _save(SETTLEMENT_PATH, snap)
        return snap

    def get_settlement_snapshot(self) -> dict:
        snap = _load(SETTLEMENT_PATH)
        if not snap:
            return {"status": "NO_SETTLEMENT_RUN", "note": "Run /trigger_settlement first"}
        return snap

settlement = _SettlementEngine()


# ---------------------------------------------------------------------------
# Stripe Binding Layer
# ---------------------------------------------------------------------------
class _StripeBindingLayer:
    def run(self) -> dict:
        events = event_bus.get_recent_events()
        mirror = {
            "synced_at":   _now(),
            "events_seen": len(events),
            "status":      "SYNCED",
            "mode":        "MIRROR_ONLY",
        }
        _save(STRIPE_PATH, mirror)
        return mirror

    def get_sync_status(self) -> dict:
        data = _load(STRIPE_PATH)
        if not data:
            return {"status": "NOT_SYNCED", "note": "No sync has run yet. Use /trigger_settlement"}
        return data

    def get_recent_events(self) -> list:
        return event_bus.get_recent_events(limit=20)

stripe = _StripeBindingLayer()


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
class _HealthCheck:
    def check_system(self) -> dict:
        checks = {}
        try:
            c = event_bus.get_event_count()
            checks["ledger"] = f"OK ({c} events)"
        except Exception as e:
            checks["ledger"] = f"FAIL: {e}"
        try:
            b = consensus.replay_balances(event_bus.get_recent_events())
            checks["consensus"] = f"OK ({len(b)} accounts)"
        except Exception as e:
            checks["consensus"] = f"FAIL: {e}"
        try:
            s = settlement.get_settlement_snapshot()
            checks["settlement"] = s.get("status", "UNKNOWN")
        except Exception as e:
            checks["settlement"] = f"FAIL: {e}"
        try:
            st = stripe.get_sync_status()
            checks["stripe_mirror"] = st.get("status", "UNKNOWN")
        except Exception as e:
            checks["stripe_mirror"] = f"FAIL: {e}"
        try:
            w = _load(WALLET_PATH)
            checks["wallet_store"] = f"OK ({len(w)} wallets)"
        except Exception as e:
            checks["wallet_store"] = f"FAIL: {e}"
        try:
            cd = _load(CARD_PATH)
            checks["card_store"] = f"OK ({len(cd)} cards)"
        except Exception as e:
            checks["card_store"] = f"FAIL: {e}"
        checks["terminal"]   = "ONLINE"
        checks["checked_at"] = _now()
        return checks

health = _HealthCheck()


# ---------------------------------------------------------------------------
# Orchestrator  (SOLE MUTATION AUTHORITY)
# ---------------------------------------------------------------------------
class _Orchestrator:
    def run(self) -> str:
        logger.info("Orchestrator: pipeline starting")
        events   = event_bus.get_recent_events()
        balances = consensus.replay_balances(events)
        snap     = consensus.build_consensus_snapshot(events, balances)
        settlement.run_settlement()
        stripe.run()
        wire_transfer_intent({
            "type":      "ORCHESTRATOR_RUN",
            "snapshot":  snap,
            "triggered": _now(),
        })
        logger.info("Orchestrator: complete — %s accounts, %s events",
                    snap["account_count"], snap["event_count"])
        return (
            f"Pipeline complete\n"
            f"Accounts: {snap['account_count']} | "
            f"Events: {snap['event_count']} | "
            f"Total value: {snap['total_value_usd']:,.2f} USD"
        )

orchestrator = _Orchestrator()


# ===========================================================================
# SYSTEM QUERY LAYER  (formats output for Telegram — no mutations here)
# ===========================================================================

def query_balance() -> str:
    try:
        events   = event_bus.get_recent_events()
        balances = consensus.replay_balances(events)
        if not balances:
            return (
                "⚠️ No balance data yet.\n\n"
                "Create a wallet with /wallet or emit a transfer with /approve\\_transfer"
            )
        lines = ["💰 *Current Balances*\n"]
        for account, amount in sorted(balances.items()):
            sign = "+" if amount >= 0 else ""
            lines.append(f"  `{account}`: *{sign}{amount:,.2f} USD*")
        snap = consensus.build_consensus_snapshot(events, balances)
        lines.append(f"\n_Total positive value: {snap['total_value_usd']:,.2f} USD_")
        return "\n".join(lines)
    except Exception as e:
        logger.error("query_balance: %s", e)
        return f"❌ Balance query failed: {e}"


def query_ledger_status() -> str:
    try:
        count  = event_bus.get_event_count()
        recent = event_bus.get_recent_events(limit=5)
        lines  = [f"📒 *Ledger Status*\n\nTotal events: `{count}`\n"]
        if recent:
            lines.append("*Last 5 events:*")
            for e in reversed(recent):
                ts  = e.get("written_at", e.get("created_at", "?"))[:19].replace("T", " ")
                typ = e.get("type", "UNKNOWN")
                lines.append(f"  `{ts}` → `{typ}`")
        return "\n".join(lines)
    except Exception as e:
        logger.error("query_ledger_status: %s", e)
        return f"❌ Ledger status failed: {e}"


def query_settlement_status() -> str:
    try:
        snap  = settlement.get_settlement_snapshot()
        lines = ["📊 *Settlement Snapshot*\n"]
        for k, v in snap.items():
            lines.append(f"  `{k}`: `{v}`")
        return "\n".join(lines)
    except Exception as e:
        logger.error("query_settlement_status: %s", e)
        return f"❌ Settlement status failed: {e}"


def query_health() -> str:
    try:
        result = health.check_system()
        lines  = ["🏥 *System Health*\n"]
        for k, v in result.items():
            ok   = any(x in str(v).upper() for x in ("OK", "ONLINE", "SYNCED", "SETTLED"))
            icon = "✅" if ok else "⚠️"
            lines.append(f"  {icon} `{k}`: `{v}`")
        return "\n".join(lines)
    except Exception as e:
        logger.error("query_health: %s", e)
        return f"❌ Health check failed: {e}"


def query_stripe_sync() -> str:
    try:
        status = stripe.get_sync_status()
        lines  = ["🔗 *Stripe Mirror Status*\n"]
        for k, v in status.items():
            lines.append(f"  `{k}`: `{v}`")
        return "\n".join(lines)
    except Exception as e:
        logger.error("query_stripe_sync: %s", e)
        return f"❌ Stripe sync query failed: {e}"


def trigger_orchestrator() -> str:
    try:
        result = orchestrator.run()
        return f"⚙️ *Orchestrator Run Complete*\n\n`{result}`"
    except Exception as e:
        logger.error("trigger_orchestrator: %s", e)
        return f"❌ Orchestrator failed: {e}"


def emit_transfer_approval(from_acct: str, to_acct: str, amount: str) -> str:
    try:
        wire_transfer_intent({
            "type": "TRANSFER_APPROVAL",
            "payload": {
                "from":   from_acct,
                "to":     to_acct,
                "amount": f"{amount} USD",
            },
        })
        return (
            f"✅ *Transfer Approval Emitted*\n\n"
            f"  From:   `{from_acct}`\n"
            f"  To:     `{to_acct}`\n"
            f"  Amount: `{amount} USD`\n\n"
            f"_Routed to event bus. Execution via orchestrator chain._"
        )
    except Exception as e:
        logger.error("emit_transfer_approval: %s", e)
        return f"❌ Transfer approval failed: {e}"


def create_wallet(telegram_user_id: str) -> str:
    try:
        wallets = _load(WALLET_PATH)
        uid     = str(telegram_user_id)
        if uid in wallets:
            w = wallets[uid]
            return (
                f"ℹ️ *Wallet Already Exists*\n\n"
                f"  Wallet ID: `{w['wallet_id']}`\n"
                f"  Balance:   `{w['balance']:.2f} USD`\n"
                f"  Card:      `{w.get('linked_card') or 'Not linked — use /create_virtual_card'}`"
            )
        wallet_id = f"OMEGA-WALLET-{uuid.uuid4().hex[:12].upper()}"
        wallet = {
            "wallet_id":     wallet_id,
            "telegram_user": uid,
            "linked_card":   None,
            "balance":       0.00,
            "created_at":    _now(),
        }
        wallets[uid] = wallet
        _save(WALLET_PATH, wallets)
        wire_transfer_intent({
            "type":          "WALLET_CREATED",
            "wallet_id":     wallet_id,
            "telegram_user": uid,
            "linked_card":   None,
            "balance":       0.00,
        })
        return (
            f"✅ *Wallet Created*\n\n"
            f"  Wallet ID: `{wallet_id}`\n"
            f"  Balance:   `0.00 USD`\n"
            f"  Status:    `ACTIVE`\n"
            f"  Card:      `Not linked — use /create\\_virtual\\_card`"
        )
    except Exception as e:
        logger.error("create_wallet: %s", e)
        return f"❌ Wallet creation failed: {e}"


def issue_virtual_card(telegram_user_id: str, pin_hash: str) -> str:
    try:
        uid     = str(telegram_user_id)
        wallets = _load(WALLET_PATH)
        cards   = _load(CARD_PATH)
        wallet    = wallets.get(uid)
        wallet_id = wallet["wallet_id"] if wallet else None
        card_id   = f"OMGCARD-{uuid.uuid4().hex[:8].upper()}"
        last4     = str(uuid.uuid4().int % 10000).zfill(4)
        issued_at = _now()
        card = {
            "card_id":    card_id,
            "last4":      last4,
            "network":    "VISA",
            "status":     "ACTIVE",
            "wallet_id":  wallet_id,
            "pin_hash":   pin_hash,
            "created_at": issued_at,
        }
        cards[uid] = card
        _save(CARD_PATH, cards)
        wire_transfer_intent({
            "type":       "CARD_ISSUED",
            "network":    "VISA",
            "status":     "ACTIVE",
            "card_id":    card_id,
            "wallet_id":  wallet_id,
            "created_at": issued_at,
        })
        if wallet:
            wallet["linked_card"] = card_id
            wallets[uid] = wallet
            _save(WALLET_PATH, wallets)
            wire_transfer_intent({
                "type":      "CARD_LINKED_TO_WALLET",
                "wallet_id": wallet_id,
                "card_id":   card_id,
                "linked_at": issued_at,
            })
        return (
            f"💳 *Virtual Card Issued*\n\n"
            f"  Network:   `VISA`\n"
            f"  Card ID:   `{card_id}`\n"
            f"  Last 4:    `**** **** **** {last4}`\n"
            f"  Status:    `ACTIVE`\n"
            f"  Wallet:    `{wallet_id or 'None — create /wallet first'}`\n"
            f"  PIN:       `Set ✅ (SHA-256 hashed)`\n"
            f"  Issued:    `{issued_at[:19].replace('T',' ')} UTC`\n\n"
            f"_Ledger event recorded. Card linked to wallet._"
        )
    except Exception as e:
        logger.error("issue_virtual_card: %s", e)
        return f"❌ Card issuance failed: {e}"


# ===========================================================================
# TELEGRAM HANDLERS
# ===========================================================================

PIN_SET, PIN_CONFIRM = range(2)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "⚡ *OMEGA AI FINANCIAL CORE*\n"
        "_Operator Terminal v1_\n\n"
        "*Commands:*\n"
        "  /balance — Consensus balances\n"
        "  /ledger\\_status — Ledger event count\n"
        "  /settlement\\_status — Settlement snapshot\n"
        "  /run\\_health\\_check — System health\n"
        "  /trigger\\_settlement — Run full pipeline\n"
        "  /view\\_stripe\\_sync — Stripe mirror status\n"
        "  /approve\\_transfer `<from> <to> <amount>`\n"
        "  /wallet — Create internal wallet\n"
        "  /create\\_virtual\\_card — Issue VISA card\n\n"
        "_All mutations route via orchestrator._",
        parse_mode="Markdown",
    )


async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(query_balance(), parse_mode="Markdown")


async def cmd_ledger_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(query_ledger_status(), parse_mode="Markdown")


async def cmd_settlement_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(query_settlement_status(), parse_mode="Markdown")


async def cmd_run_health_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(query_health(), parse_mode="Markdown")


async def cmd_trigger_settlement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚙️ Running orchestrator pipeline...", parse_mode="Markdown")
    await update.message.reply_text(trigger_orchestrator(), parse_mode="Markdown")


async def cmd_view_stripe_sync(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(query_stripe_sync(), parse_mode="Markdown")


async def cmd_approve_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args or len(args) < 3:
        await update.message.reply_text(
            "⚠️ *Usage:* `/approve_transfer <from> <to> <amount>`\n\n"
            "*Example:*\n`/approve_transfer ACC-001 ACC-002 500.00`",
            parse_mode="Markdown",
        )
        return
    from_acct = args[0]
    to_acct   = args[1]
    try:
        amount = f"{float(args[2]):,.2f}"
    except ValueError:
        await update.message.reply_text("❌ Amount must be a number.", parse_mode="Markdown")
        return
    await update.message.reply_text(
        emit_transfer_approval(from_acct, to_acct, amount), parse_mode="Markdown"
    )


async def cmd_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = str(update.effective_user.id)
    await update.message.reply_text(create_wallet(uid), parse_mode="Markdown")


async def cmd_create_virtual_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid   = str(update.effective_user.id)
    cards = _load(CARD_PATH)
    if uid in cards:
        c = cards[uid]
        await update.message.reply_text(
            f"ℹ️ *Card Already Exists*\n\n"
            f"  Card ID: `{c['card_id']}`\n"
            f"  Last 4:  `**** **** **** {c['last4']}`\n"
            f"  Network: `{c['network']}`\n"
            f"  Status:  `{c['status']}`",
            parse_mode="Markdown",
        )
        return ConversationHandler.END
    await update.message.reply_text(
        "💳 *Card Issuance — Step 1 of 2*\n\n"
        "Enter a *4-digit PIN* for your virtual card:\n"
        "_(message deleted immediately for security)_",
        parse_mode="Markdown",
    )
    return PIN_SET


async def pin_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pin = update.message.text.strip()
    try:
        await update.message.delete()
    except Exception:
        pass
    if not pin.isdigit() or len(pin) != 4:
        await update.message.reply_text("❌ PIN must be exactly 4 digits. Try again:")
        return PIN_SET
    context.user_data["pending_pin_hash"] = _hash_pin(pin)
    await update.message.reply_text(
        "🔐 *Step 2 of 2* — Confirm your 4-digit PIN:",
        parse_mode="Markdown",
    )
    return PIN_CONFIRM


async def pin_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pin = update.message.text.strip()
    try:
        await update.message.delete()
    except Exception:
        pass
    if not pin.isdigit() or len(pin) != 4:
        await update.message.reply_text("❌ PIN must be exactly 4 digits. Try again:")
        return PIN_CONFIRM
    stored_hash  = context.user_data.get("pending_pin_hash")
    confirm_hash = _hash_pin(pin)
    if confirm_hash != stored_hash:
        context.user_data.pop("pending_pin_hash", None)
        await update.message.reply_text(
            "❌ PINs do not match. Cancelled.\nUse /create\\_virtual\\_card to retry.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END
    uid    = str(update.effective_user.id)
    result = issue_virtual_card(uid, confirm_hash)
    context.user_data.pop("pending_pin_hash", None)
    await update.message.reply_text(result, parse_mode="Markdown")
    return ConversationHandler.END


async def cancel_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("pending_pin_hash", None)
    await update.message.reply_text("❌ Card issuance cancelled.")
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            f"⚠️ Error: `{type(context.error).__name__}: {context.error}`",
            parse_mode="Markdown",
        )


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "\n\nTELEGRAM_BOT_TOKEN is not set.\n"
            "Create a .env file in this directory with:\n"
            "  TELEGRAM_BOT_TOKEN=your_token_here\n"
        )

    app = ApplicationBuilder().token(token).build()

    card_conv = ConversationHandler(
        entry_points=[CommandHandler("create_virtual_card", cmd_create_virtual_card)],
        states={
            PIN_SET:     [MessageHandler(filters.TEXT & ~filters.COMMAND, pin_set)],
            PIN_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, pin_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel_card)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start",              cmd_start))
    app.add_handler(CommandHandler("balance",            cmd_balance))
    app.add_handler(CommandHandler("ledger_status",      cmd_ledger_status))
    app.add_handler(CommandHandler("settlement_status",  cmd_settlement_status))
    app.add_handler(CommandHandler("run_health_check",   cmd_run_health_check))
    app.add_handler(CommandHandler("trigger_settlement", cmd_trigger_settlement))
    app.add_handler(CommandHandler("view_stripe_sync",   cmd_view_stripe_sync))
    app.add_handler(CommandHandler("approve_transfer",   cmd_approve_transfer))
    app.add_handler(CommandHandler("wallet",             cmd_wallet))
    app.add_handler(card_conv)
    app.add_error_handler(error_handler)

    logger.info("OMEGA Operator Terminal online — polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()		

# =========================================================
# OMEGA PHASE 3 EVENT WIRING IMPORTS
# =========================================================

from omega_event_wiring_patch_v1 import (
    wire_wallet_created,
    wire_transfer_intent,
    wire_card_issued,
    wire_settlement_event,
    wire_qr_intent
)


# =========================================================
# OMEGA EVENT BUS CORE EXTENSION (SAFE READ + WRITE LAYER)
# =========================================================

class _EventBus:
    def get_recent_events(self, limit: int = 100) -> list:
        events = _load(LEDGER_PATH)
        return events[-limit:] if isinstance(events, list) else []

    def write_event(self, event: dict) -> None:
        events = _load(LEDGER_PATH)

        if not isinstance(events, list):
            events = []

        event.setdefault("event_id", str(uuid.uuid4()))
        event.setdefault("written_at", _now())

        events.append(event)
        _save(LEDGER_PATH, events)

    def get_event_count(self) -> int:
        events = _load(LEDGER_PATH)
        return len(events) if isinstance(events, list) else 0


event_bus = _EventBus()


# =========================================================
# OMEGA CFO SETTLEMENT ACCOUNT BRIDGE
# =========================================================

def get_real_financial_accounts():

    try:
        snapshot = settlement.run_settlement()

        balances = snapshot.get("settled_balances", {})

        return {
            "OMEGA_TREASURY": balances.get("OMEGA_TREASURY", 0.0),
            "OMEGA_CREDIT": balances.get("OMEGA_CREDIT", 0.0),
            "OMEGA_RESERVE": balances.get("OMEGA_RESERVE", 0.0),
            "OMEGA_INVESTMENT": balances.get("OMEGA_INVESTMENT", 0.0),
            "THOMAS_LH": balances.get("THOMAS_LH", 0.0)
        }

    except Exception as e:
        logger.error(f"CFO settlement bridge failed: {e}")
        return {}


async def cfo_dashboard(update, context):

    accounts = get_real_financial_accounts()

    lines = [
        "🏦 OMEGA CFO TERMINAL",
        "",
    ]

    for account, balance in accounts.items():
        lines.append(
            f"  {account}: ${balance:,.2f} USD"
        )

    await update.message.reply_text(
        "\n".join(lines)
    )


# =========================================================
# CFO DASHBOARD COMMAND REGISTRATION
# =========================================================

try:
    application.add_handler(
        CommandHandler(
            "cfo_dashboard",
            cfo_dashboard
        )
    )
except Exception as e:
    logger.error(f"CFO dashboard handler registration failed: {e}")

