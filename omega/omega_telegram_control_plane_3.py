import os
import logging
import uuid
import bcrypt
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

from omega_transactional_event_store import get_events

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omega-control-plane")

# =========================
# STATE
# =========================
USERS = {}
SESSIONS = {}

# =========================
# AUTH CHECK
# =========================
def require_auth(user_id: int):
    session = SESSIONS.get(user_id)

    if not session:
        return None

    if session["expires"] < datetime.utcnow():
        del SESSIONS[user_id]
        return None

    return session["account_id"]

# =========================
# BALANCE PROJECTION (SAFE MVP)
# =========================
def compute_balance(account_id: str):
    events = get_events(account_id)

    balance = 0.0

    for e in events:
        t = e.get("event_type", "")
        payload = e.get("payload", {})

        amount = float(payload.get("amount", 0))

        # deterministic ledger rules (NO external dependency)
        if t in ["AUTH_CREATED", "PAYMENT_CAPTURED"]:
            balance += amount

        elif t in ["AUTH_CAPTURED"]:
            balance -= amount

        elif t in ["AUTH_REVERSED", "AUTH_EXPIRED"]:
            balance += 0  # neutral for MVP stability

    return balance, len(events)

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏦 OMEGA FINANCIAL CONTROL PLANE\n"
        "/setpin <pin>\n"
        "/login <pin>\n"
        "/wallet\n"
        "/transactions\n"
        "/pending"
    )

# =========================
# SET PIN
# =========================
async def setpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /setpin <pin>")
        return

    pin = context.args[0].encode()
    pin_hash = bcrypt.hashpw(pin, bcrypt.gensalt())

    USERS[user_id] = {
        "account_id": str(uuid.uuid4()),
        "pin_hash": pin_hash
    }

    await update.message.reply_text("🔐 PIN set + account created")

# =========================
# LOGIN
# =========================
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /login <pin>")
        return

    pin = context.args[0].encode()
    user = USERS.get(user_id)

    if not user:
        await update.message.reply_text("❌ No account. Use /setpin first.")
        return

    if not bcrypt.checkpw(pin, user["pin_hash"]):
        await update.message.reply_text("❌ Invalid PIN")
        return

    SESSIONS[user_id] = {
        "account_id": user["account_id"],
        "expires": datetime.utcnow() + timedelta(hours=2)
    }

    await update.message.reply_text("✅ Authenticated")

# =========================
# WALLET
# =========================
async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    account_id = require_auth(user_id)

    if not account_id:
        await update.message.reply_text("🔒 Unauthorized")
        return

    balance, count = compute_balance(account_id)

    await update.message.reply_text(
        f"💼 Wallet\n"
        f"Balance: ${balance:.2f}\n"
        f"Events: {count}"
    )

# =========================
# TRANSACTIONS
# =========================
async def transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    account_id = require_auth(user_id)

    if not account_id:
        await update.message.reply_text("🔒 Unauthorized")
        return

    events = get_events(account_id)

    msg = "📊 TRANSACTIONS\n\n"

    for e in events[-10:]:
        msg += f"{e['event_type']} | {e.get('payload', {}).get('amount', 0)}\n"

    await update.message.reply_text(msg)

# =========================
# PENDING
# =========================
async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    account_id = require_auth(user_id)

    if not account_id:
        await update.message.reply_text("🔒 Unauthorized")
        return

    keyboard = [[
        InlineKeyboardButton("APPROVE", callback_data="approve"),
        InlineKeyboardButton("REJECT", callback_data="reject")
    ]]

    await update.message.reply_text(
        "⚠️ Pending action",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# CALLBACK
# =========================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"ACTION: {query.data}")

# =========================
# MAIN
# =========================
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise Exception("Missing TELEGRAM_BOT_TOKEN")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setpin", setpin))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("wallet", wallet))
    app.add_handler(CommandHandler("transactions", transactions))
    app.add_handler(CommandHandler("pending", pending))

    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("🚀 Omega Control Plane ACTIVE")
    app.run_polling()

if __name__ == "__main__":
    main()
