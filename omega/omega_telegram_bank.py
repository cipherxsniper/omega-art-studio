import os
import uuid
import bcrypt
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from omega_transactional_event_store import get_events

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omega-bank")

# =========================
# STATE (CONTROL PLANE ONLY)
# =========================
PIN_STORE = {}
SESSIONS = {}
PENDING_INPUT = {}
PENDING_APPROVALS = {}
CARDS = {}

# =========================
# AUTH
# =========================
def require_auth(user_id: int):
    session = SESSIONS.get(user_id)

    if not session:
        return False

    if session["expires"] < datetime.utcnow():
        del SESSIONS[user_id]
        return False

    return True

def ensure_wallet(user_id: int):
    if user_id not in CARDS:
        CARDS[user_id] = {
            "wallet_id": str(uuid.uuid4()),
            "card_id": str(uuid.uuid4()),
            "created_at": datetime.utcnow().isoformat()
        }

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_wallet(user_id)

    await update.message.reply_text(
        "🏦 OMEGA FINANCIAL NETWORK\n\n"
        "Commands:\n"
        "/setpin <pin>\n"
        "/login <pin>\n"
        "/wallet\n"
        "/transactions\n"
        "/card\n"
        "/pending\n"
    )

# =========================
# PIN
# =========================
async def setpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        PENDING_INPUT[user_id] = "setpin"
        await update.message.reply_text("🔐 Send PIN:")
        return

    pin = context.args[0]
    PIN_STORE[user_id] = bcrypt.hashpw(pin.encode(), bcrypt.gensalt())
    await update.message.reply_text("🔐 PIN SET")

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        PENDING_INPUT[user_id] = "login"
        await update.message.reply_text("🔑 Send PIN:")
        return

    pin = context.args[0]
    stored = PIN_STORE.get(user_id)

    if not stored:
        await update.message.reply_text("❌ No PIN set")
        return

    if bcrypt.checkpw(pin.encode(), stored):
        SESSIONS[user_id] = {
            "token": str(uuid.uuid4()),
            "expires": datetime.utcnow() + timedelta(hours=2)
        }
        await update.message.reply_text("✅ AUTHORIZED")
    else:
        await update.message.reply_text("❌ INVALID PIN")

# =========================
# WALLET (REAL LEDGER VIEW)
# =========================
async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not require_auth(user_id):
        await update.message.reply_text("🔒 UNAUTHORIZED")
        return

    events = get_events()

    balance = sum(
        e.get("payload", {}).get("amount", 0)
        for e in events
    )

    await update.message.reply_text(
        f"💼 WALLET\n"
        f"Balance: ${balance}\n"
        f"Events: {len(events)}"
    )

# =========================
# TRANSACTIONS
# =========================
async def transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not require_auth(user_id):
        await update.message.reply_text("🔒 UNAUTHORIZED")
        return

    events = get_events()[-5:]

    msg = "📊 LAST EVENTS:\n\n"
    for e in events:
        msg += f"{e.get('event_type')} | {e.get('event_id')}\n"

    await update.message.reply_text(msg)

# =========================
# VIRTUAL CARD (LEDGER OBJECT)
# =========================
async def card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not require_auth(user_id):
        await update.message.reply_text("🔒 UNAUTHORIZED")
        return

    ensure_wallet(user_id)
    c = CARDS[user_id]

    await update.message.reply_text(
        "💳 OMEGA VIRTUAL CARD\n\n"
        f"Wallet ID: {c['wallet_id']}\n"
        f"Card ID: {c['card_id']}\n"
        f"Created: {c['created_at']}"
    )

# =========================
# PENDING APPROVALS
# =========================
async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not require_auth(user_id):
        await update.message.reply_text("🔒 UNAUTHORIZED")
        return

    keyboard = [
        [
            InlineKeyboardButton("APPROVE", callback_data="approve"),
            InlineKeyboardButton("REJECT", callback_data="reject")
        ]
    ]

    await update.message.reply_text(
        "⚠️ PENDING ACTION",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# CALLBACK HANDLER
# =========================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "approve":
        await query.edit_message_text("✅ APPROVED")
    else:
        await query.edit_message_text("❌ REJECTED")

# =========================
# MAIN
# =========================
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise Exception("Missing TELEGRAM_BOT_TOKEN in .env")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setpin", setpin))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("wallet", wallet))
    app.add_handler(CommandHandler("transactions", transactions))
    app.add_handler(CommandHandler("card", card))
    app.add_handler(CommandHandler("pending", pending))

    app.add_handler(CallbackQueryHandler(callback))

    logger.info("🚀 Omega Bank Control Plane LIVE")
    app.run_polling()

if __name__ == "__main__":
    main()
