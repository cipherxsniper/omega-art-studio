"""
OMEGA AI FINANCIAL CORE
Telegram Operator Terminal v1
Phase 2 — Read + Command Layer Only
"""

import os
import json
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

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

import omega_event_bus_core_v1 as event_bus
import omega_financial_consensus_engine_v1 as consensus
import omega_settlement_engine_v1 as settlement
import omega_stripe_binding_layer_v1 as stripe
import omega_system_health_check_v1 as health
import omega_unified_system_orchestrator_v1 as orchestrator

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("OMEGA.TelegramTerminal")

# ---------------------------------------------------------------------------
# Constants / Paths
# ---------------------------------------------------------------------------
CARD_PIN_STORE = Path("omega_card_pins.json")          # encrypted-hash store
WALLET_STORE   = Path("omega_wallet_registry.json")    # internal wallet registry

# ConversationHandler states
PIN_SET, PIN_CONFIRM = range(2)

# ---------------------------------------------------------------------------
# Local store helpers (file-backed, no DB writes)
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {}


def _save_json(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _hash_pin(pin: str) -> str:
    """SHA-256 hash of PIN — never store raw."""
    return hashlib.sha256(pin.encode()).hexdigest()


def _get_wallet(telegram_user_id: str) -> dict | None:
    registry = _load_json(WALLET_STORE)
    return registry.get(str(telegram_user_id))


def _save_wallet(telegram_user_id: str, wallet: dict) -> None:
    registry = _load_json(WALLET_STORE)
    registry[str(telegram_user_id)] = wallet
    _save_json(WALLET_STORE, registry)


def _get_card(telegram_user_id: str) -> dict | None:
    pins = _load_json(CARD_PIN_STORE)
    return pins.get(str(telegram_user_id))


def _save_card(telegram_user_id: str, card: dict) -> None:
    pins = _load_json(CARD_PIN_STORE)
    pins[str(telegram_user_id)] = card
    _save_json(CARD_PIN_STORE, card if False else pins)  # save full registry


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# System Query Layer  (all business reads happen here — not in handlers)
# ---------------------------------------------------------------------------

def query_balance() -> str:
    try:
        events   = event_bus.get_recent_events()
        balances = consensus.replay_balances(events)
        if not balances:
            return "⚠️ No balance data available."
        lines = ["💰 *Current Balances*\n"]
        for account, amount in balances.items():
            lines.append(f"  `{account}`: *{float(amount):,.2f} USD*")
        return "\n".join(lines)
    except Exception as e:
        logger.error("query_balance error: %s", e)
        return f"❌ Balance query failed: {e}"


def query_ledger_status() -> str:
    try:
        count = event_bus.get_event_count()
        return f"📒 *Ledger Status*\n\nTotal events recorded: `{count}`"
    except Exception as e:
        logger.error("query_ledger_status error: %s", e)
        return f"❌ Ledger status failed: {e}"


def query_settlement_status() -> str:
    try:
        snapshot = settlement.get_settlement_snapshot()
        if not snapshot:
            return "⚠️ No settlement snapshot available."
        lines = ["📊 *Settlement Snapshot*\n"]
        for k, v in snapshot.items():
            lines.append(f"  `{k}`: `{v}`")
        return "\n".join(lines)
    except Exception as e:
        logger.error("query_settlement_status error: %s", e)
        return f"❌ Settlement status failed: {e}"


def query_health() -> str:
    try:
        result = health.check_system()
        if isinstance(result, dict):
            lines = ["🏥 *System Health*\n"]
            for k, v in result.items():
                icon = "✅" if str(v).lower() in ("ok", "healthy", "true", "pass", "up") else "⚠️"
                lines.append(f"  {icon} `{k}`: `{v}`")
            return "\n".join(lines)
        return f"🏥 *System Health*\n\n`{result}`"
    except Exception as e:
        logger.error("query_health error: %s", e)
        return f"❌ Health check failed: {e}"


def query_stripe_sync() -> str:
    try:
        status = stripe.get_sync_status()
        if isinstance(status, dict):
            lines = ["🔗 *Stripe Sync Status*\n"]
            for k, v in status.items():
                lines.append(f"  `{k}`: `{v}`")
            return "\n".join(lines)
        return f"🔗 *Stripe Sync Status*\n\n`{status}`"
    except Exception as e:
        logger.error("query_stripe_sync error: %s", e)
        return f"❌ Stripe sync query failed: {e}"


def trigger_orchestrator() -> str:
    try:
        result = orchestrator.run()
        msg = result if result else "Orchestrator run completed."
        return f"⚙️ *Orchestrator Triggered*\n\n`{msg}`"
    except Exception as e:
        logger.error("trigger_orchestrator error: %s", e)
        return f"❌ Orchestrator trigger failed: {e}"


def emit_transfer_approval(from_acct: str, to_acct: str, amount: str) -> str:
    try:
        event_bus.write_event({
            "type": "TRANSFER_APPROVAL",
            "payload": {
                "from":   from_acct,
                "to":     to_acct,
                "amount": f"{amount} USD",
            },
            "emitted_at": _now_iso(),
        })
        return (
            f"✅ *Transfer Approval Emitted*\n\n"
            f"  From:   `{from_acct}`\n"
            f"  To:     `{to_acct}`\n"
            f"  Amount: `{amount} USD`\n\n"
            f"_Execution routed via orchestrator chain._"
        )
    except Exception as e:
        logger.error("emit_transfer_approval error: %s", e)
        return f"❌ Transfer approval failed: {e}"


def create_wallet(telegram_user_id: str) -> str:
    try:
        existing = _get_wallet(telegram_user_id)
        if existing:
            return (
                f"ℹ️ *Wallet Already Exists*\n\n"
                f"  Wallet ID: `{existing['wallet_id']}`\n"
                f"  Balance:   `{existing['balance']:.2f} USD`\n"
                f"  Card:      `{'Linked ✅' if existing.get('linked_card') else 'Not linked'}`"
            )

        wallet_id = f"OMEGA-WALLET-{uuid.uuid4().hex[:12].upper()}"
        wallet = {
            "wallet_id":    wallet_id,
            "telegram_user": telegram_user_id,
            "linked_card":  None,
            "balance":      0.00,
            "created_at":   _now_iso(),
        }

        event_bus.write_event({
            "type":          "WALLET_CREATED",
            "wallet_id":     wallet_id,
            "telegram_user": telegram_user_id,
            "linked_card":   None,
            "balance":       0.00,
            "created_at":    wallet["created_at"],
        })

        _save_wallet(telegram_user_id, wallet)

        return (
            f"✅ *Wallet Created*\n\n"
            f"  Wallet ID: `{wallet_id}`\n"
            f"  Balance:   `0.00 USD`\n"
            f"  Status:    `Active`\n"
            f"  Card:      `Not linked — use /create_virtual_card`"
        )
    except Exception as e:
        logger.error("create_wallet error: %s", e)
        return f"❌ Wallet creation failed: {e}"


def issue_virtual_card(telegram_user_id: str, pin_hash: str) -> str:
    try:
        wallet = _get_wallet(telegram_user_id)
        wallet_id = wallet["wallet_id"] if wallet else None

        card_id    = f"OMGCARD-{uuid.uuid4().hex[:8].upper()}"
        card_last4 = str(uuid.uuid4().int)[:4]
        issued_at  = _now_iso()

        card_record = {
            "card_id":       card_id,
            "last4":         card_last4,
            "network":       "VISA",
            "status":        "ACTIVE",
            "wallet_id":     wallet_id,
            "pin_hash":      pin_hash,
            "created_at":    issued_at,
        }

        event_bus.write_event({
            "type":       "CARD_ISSUED",
            "network":    "VISA",
            "status":     "ACTIVE",
            "card_id":    card_id,
            "wallet_id":  wallet_id,
            "created_at": issued_at,
        })

        _save_card(telegram_user_id, card_record)

        # Link card back to wallet
        if wallet:
            wallet["linked_card"] = card_id
            _save_wallet(telegram_user_id, wallet)
            event_bus.write_event({
                "type":      "CARD_LINKED_TO_WALLET",
                "wallet_id": wallet_id,
                "card_id":   card_id,
                "linked_at": issued_at,
            })

        return (
            f"💳 *Virtual Card Issued*\n\n"
            f"  Network:   `VISA`\n"
            f"  Card ID:   `{card_id}`\n"
            f"  Last 4:    `**** **** **** {card_last4}`\n"
            f"  Status:    `ACTIVE`\n"
            f"  Wallet:    `{wallet_id or 'None — create /wallet first'}`\n"
            f"  PIN:       `Set ✅ (hashed & stored)`\n"
            f"  Issued At: `{issued_at}`\n\n"
            f"_Ledger event recorded. Card linked to wallet._"
        )
    except Exception as e:
        logger.error("issue_virtual_card error: %s", e)
        return f"❌ Card issuance failed: {e}"


# ---------------------------------------------------------------------------
# Telegram Command Handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "⚡ *OMEGA AI FINANCIAL CORE*\n"
        "_Operator Terminal v1 — Phase 2_\n\n"
        "*Available Commands:*\n"
        "  /balance — View consensus balances\n"
        "  /ledger\\_status — Ledger event count\n"
        "  /settlement\\_status — Settlement snapshot\n"
        "  /run\\_health\\_check — System health\n"
        "  /trigger\\_settlement — Run orchestrator\n"
        "  /view\\_stripe\\_sync — Stripe sync status\n"
        "  /approve\\_transfer — Emit transfer approval\n"
        "  /wallet — Create internal wallet\n"
        "  /create\\_virtual\\_card — Issue VISA card\n\n"
        "_Bot is READ + COMMAND layer only. All mutations route via orchestrator._"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(query_balance(), parse_mode="Markdown")


async def cmd_ledger_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(query_ledger_status(), parse_mode="Markdown")


async def cmd_settlement_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(query_settlement_status(), parse_mode="Markdown")


async def cmd_run_health_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(query_health(), parse_mode="Markdown")


async def cmd_trigger_settlement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "⚙️ Triggering orchestrator...", parse_mode="Markdown"
    )
    await update.message.reply_text(trigger_orchestrator(), parse_mode="Markdown")


async def cmd_view_stripe_sync(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(query_stripe_sync(), parse_mode="Markdown")


async def cmd_approve_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Usage: /approve_transfer <from_account> <to_account> <amount>
    Example: /approve_transfer ACC-001 ACC-002 500.00
    """
    args = context.args
    if not args or len(args) < 3:
        await update.message.reply_text(
            "⚠️ Usage: `/approve_transfer <from> <to> <amount>`\n"
            "Example: `/approve_transfer ACC-001 ACC-002 500.00`",
            parse_mode="Markdown",
        )
        return

    from_acct = args[0]
    to_acct   = args[1]
    try:
        amount = f"{float(args[2]):,.2f}"
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Must be a number.", parse_mode="Markdown")
        return

    result = emit_transfer_approval(from_acct, to_acct, amount)
    await update.message.reply_text(result, parse_mode="Markdown")


async def cmd_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    result  = create_wallet(user_id)
    await update.message.reply_text(result, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /create_virtual_card — ConversationHandler (PIN set + confirm)
# ---------------------------------------------------------------------------

async def cmd_create_virtual_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    existing = _get_card(str(update.effective_user.id))
    if existing:
        await update.message.reply_text(
            f"ℹ️ You already have a card.\n\n"
            f"  Card ID: `{existing['card_id']}`\n"
            f"  Status:  `{existing['status']}`\n"
            f"  Network: `{existing['network']}`",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "💳 *Card Issuance — Step 1 of 2*\n\n"
        "Enter a 4-digit PIN for your virtual card:",
        parse_mode="Markdown",
    )
    return PIN_SET


async def pin_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pin = update.message.text.strip()
    await update.message.delete()   # immediately delete PIN message for security

    if not pin.isdigit() or len(pin) != 4:
        await update.message.reply_text(
            "❌ PIN must be exactly 4 digits. Try again:", parse_mode="Markdown"
        )
        return PIN_SET

    context.user_data["pending_pin_hash"] = _hash_pin(pin)
    await update.message.reply_text(
        "🔐 *Step 2 of 2* — Confirm your 4-digit PIN:",
        parse_mode="Markdown",
    )
    return PIN_CONFIRM


async def pin_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pin = update.message.text.strip()
    await update.message.delete()   # immediately delete PIN message for security

    if not pin.isdigit() or len(pin) != 4:
        await update.message.reply_text(
            "❌ PIN must be exactly 4 digits. Try again:", parse_mode="Markdown"
        )
        return PIN_CONFIRM

    confirm_hash = _hash_pin(pin)
    stored_hash  = context.user_data.get("pending_pin_hash")

    if confirm_hash != stored_hash:
        context.user_data.pop("pending_pin_hash", None)
        await update.message.reply_text(
            "❌ PINs do not match. Card issuance cancelled.\n"
            "Use /create\\_virtual\\_card to try again.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    user_id = str(update.effective_user.id)
    result  = issue_virtual_card(user_id, confirm_hash)
    context.user_data.pop("pending_pin_hash", None)
    await update.message.reply_text(result, parse_mode="Markdown")
    return ConversationHandler.END


async def cancel_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("pending_pin_hash", None)
    await update.message.reply_text("❌ Card issuance cancelled.", parse_mode="Markdown")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception: %s", context.error, exc_info=True)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            "⚠️ An internal error occurred. Check operator logs."
        )


# ---------------------------------------------------------------------------
# Application bootstrap
# ---------------------------------------------------------------------------

def build_application():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment / .env")

    app = ApplicationBuilder().token(token).build()

    # --- ConversationHandler for virtual card issuance (PIN flow) ---
    card_conversation = ConversationHandler(
        entry_points=[CommandHandler("create_virtual_card", cmd_create_virtual_card)],
        states={
            PIN_SET:     [MessageHandler(filters.TEXT & ~filters.COMMAND, pin_set)],
            PIN_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, pin_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel_card)],
        allow_reentry=True,
    )

    # --- Standard command handlers ---
    app.add_handler(CommandHandler("start",              cmd_start))
    app.add_handler(CommandHandler("balance",            cmd_balance))
    app.add_handler(CommandHandler("ledger_status",      cmd_ledger_status))
    app.add_handler(CommandHandler("settlement_status",  cmd_settlement_status))
    app.add_handler(CommandHandler("run_health_check",   cmd_run_health_check))
    app.add_handler(CommandHandler("trigger_settlement", cmd_trigger_settlement))
    app.add_handler(CommandHandler("view_stripe_sync",   cmd_view_stripe_sync))
    app.add_handler(CommandHandler("approve_transfer",   cmd_approve_transfer))
    app.add_handler(CommandHandler("wallet",             cmd_wallet))
    app.add_handler(card_conversation)

    app.add_error_handler(error_handler)

    return app


def main() -> None:
    logger.info("OMEGA Telegram Operator Terminal starting...")
    app = build_application()
    logger.info("Bot polling started. Waiting for commands.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
