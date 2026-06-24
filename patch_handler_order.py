path = "/data/data/com.termux/files/home/omega_v10.py"
content = open(path).read()

old = '''        app.add_handler(CallbackQueryHandler(master_button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_assistant_query))
        app.add_handler(CommandHandler("trading", cmd_trading))
        app.add_handler(CommandHandler("cards", cmd_cards))
        app.add_handler(CallbackQueryHandler(cards_button_handler, pattern="^card_"))
        app.add_handler(CommandHandler("cards", cmd_cards))
        app.add_handler(CallbackQueryHandler(cards_button_handler, pattern="^card_"))
        app.add_handler(CommandHandler("finance", cmd_finance))'''

new = '''        app.add_handler(CallbackQueryHandler(cards_button_handler, pattern="^card_"), group=1)
        app.add_handler(CallbackQueryHandler(trading_button_handler, pattern="^trade_"), group=1)
        app.add_handler(CallbackQueryHandler(finance_button_handler, pattern="^finance_"), group=1)
        app.add_handler(CallbackQueryHandler(master_button_handler), group=2)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_assistant_query))
        app.add_handler(CommandHandler("trading", cmd_trading))
        app.add_handler(CommandHandler("cards", cmd_cards))
        app.add_handler(CommandHandler("finance", cmd_finance))'''

assert old in content, "anchor not found"
content = content.replace(old, new)
open(path, "w").write(content)
print("Handler order fixed")
