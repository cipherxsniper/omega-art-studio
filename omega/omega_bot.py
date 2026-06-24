import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

from core.external_accounts import ExternalAccountStore

TOKEN = os.getenv("OMEGA_TELEGRAM_TOKEN")

store = ExternalAccountStore()
sessions = {}

MENU = ReplyKeyboardMarkup(
    [
        ["💰 Balance", "💸 Send Money"],
        ["🏦 Link Bank", "💰 Add Money"],
        ["📄 Profile"]
    ],
    resize_keyboard=True
)

# -------------------------
# START
# -------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    sessions[uid] = {"state": "PIN"}

    await update.message.reply_text("🔐 Enter PIN:")

# -------------------------
# MAIN ROUTER
# -------------------------

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()

    session = sessions.get(uid, {"state": "PIN"})

    # ---------------- PIN ----------------
    if session["state"] == "PIN":
        if text == "1709":
            session["state"] = "AUTH"
            sessions[uid] = session

            await update.message.reply_text(
                "🔓 Access Granted\nWelcome to Omega Bank",
                reply_markup=MENU
            )
        else:
            await update.message.reply_text("❌ Invalid PIN")
        return

    # ---------------- AUTH MENU ----------------
    if session["state"] == "AUTH":

        if text == "🏦 Link Bank":
            session["state"] = "BANK_NAME"
            sessions[uid] = session
            await update.message.reply_text("🏦 Enter name of your bank:")
            return

        if text == "💰 Add Money":
            if "bank_linked" not in session:
                await update.message.reply_text("❌ Link a bank first")
                return

            session["state"] = "ADD_FUNDS"
            sessions[uid] = session
            await update.message.reply_text("💰 Enter amount to add:")
            return

        if text == "💰 Balance":
            await update.message.reply_text("💰 Balance: $0.00 (ledger engine)")
            return

        if text == "📄 Profile":
            await update.message.reply_text(str(session))
            return

    # ---------------- BANK LINK FLOW ----------------

    if session["state"] == "BANK_NAME":
        session["bank_name"] = text
        session["state"] = "ACCOUNT_NUMBER"
        sessions[uid] = session

        await update.message.reply_text("🏦 Enter account number:")
        return

    if session["state"] == "ACCOUNT_NUMBER":
        if not text.isdigit():
            await update.message.reply_text("❌ Account number must be numeric")
            return

        session["account_number"] = text
        session["state"] = "ROUTING_NUMBER"
        sessions[uid] = session

        await update.message.reply_text("🏦 Enter routing number:")
        return

    if session["state"] == "ROUTING_NUMBER":
        if not text.isdigit():
            await update.message.reply_text("❌ Routing number must be numeric")
            return

        session["routing_number"] = text

        # SAVE BANK
        store.add_account(
            id=str(uid),
            user_id=str(uid),
            provider=session["bank_name"],
            label="PRIMARY",
            identifier=f"{session['account_number']}|{session['routing_number']}"
        )

        session["bank_linked"] = True
        session["state"] = "AUTH"
        sessions[uid] = session

        await update.message.reply_text(
            "🏦 Bank linked successfully\nYou can now add funds",
            reply_markup=MENU
        )
        return

    # ---------------- ADD FUNDS FLOW ----------------

    if session["state"] == "ADD_FUNDS":
        if not text.isdigit():
            await update.message.reply_text("❌ Enter a valid number")
            return

        amount = float(text)

        # EVENT ONLY (NO FAKE BALANCE)
        await update.message.reply_text(
            f"💰 Deposit Requested: ${amount}\nStatus: PENDING PROCESSING (ledger event only)"
        )

        session["state"] = "AUTH"
        sessions[uid] = session
        return

# -------------------------
# BOOT
# -------------------------

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("OMEGA BANK v3 FULL STATE MACHINE ONLINE")

app.run_polling()
