path = "/data/data/com.termux/files/home/omega_v10.py"
content = open(path).read()

old = '''    elif data == "finance_cards":
        summary = get_bank_summary()
        cards = summary.get("cards", [])
        if not cards:
            text = "💳 *Virtual Cards*\\n\\n_No active cards_"
        else:
            lines = [f"  **** **** **** {c[0]}  [{c[1]}]\\n  Exp: {c[2]}" for c in cards]
            text = "💳 *Virtual Cards — ACTIVE*\\n\\n━━━━━━━━━━━━━━━━━━━━━━\\n" + "\\n\\n".join(lines)
        await query.edit_message_text(text, reply_markup=fin_back_kb, parse_mode="Markdown")'''

new = '''    elif data == "finance_cards":
        try:
            import sys as _sys
            _sys.path.insert(0, "/data/data/com.termux/files/home")
            from omega_card_engine import get_cards as _gc, ensure_card_tables as _ect
            _ect()
            cards = _gc()
            if not cards:
                text = (
                    "💳 *Virtual Cards*\\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\\n"
                    "_No cards yet._\\n\\n"
                    "Tap 💳 Issue Card to create one."
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Issue Card", callback_data="card_issue")],
                    [InlineKeyboardButton("🔙 Finance", callback_data="open_finance")],
                ])
                await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
                return
            lines = []
            for c in cards:
                token, owner, last4, em, ey, status, limit, used, ctype, issued = c[:10]
                icon = "🟢" if str(status) == "ACTIVE" else "🔴"
                avail = float(limit) - float(used)
                lines.append(
                    f"{icon} *···· {last4}* | {owner}\\n"
                    f"  Type: {ctype} | EXP: {em:02d}/{ey}\\n"
                    f"  Limit: ${float(limit):,.2f}\\n"
                    f"  Used:  ${float(used):,.2f}\\n"
                    f"  Avail: ${avail:,.2f}\\n"
                    f"  Status: {status}"
                )
            text = (
                "💳 *OMEGA VIRTUAL CARDS*\\n"
                "━━━━━━━━━━━━━━━━━━━━━━\\n"
                f"  Total: {len(cards)} card(s)\\n"
                "━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
                + "\\n\\n".join(lines)
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Issue Card", callback_data="card_issue"),
                 InlineKeyboardButton("📋 List All", callback_data="card_list")],
                [InlineKeyboardButton("📊 Transactions", callback_data="card_txns"),
                 InlineKeyboardButton("🔍 Audit", callback_data="card_audit")],
                [InlineKeyboardButton("🔙 Finance", callback_data="open_finance")],
            ])
            await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
            return
        except Exception as e:
            text = f"❌ Card error: {e}"
        await query.edit_message_text(text, reply_markup=fin_back_kb, parse_mode="Markdown")'''

assert old in content, "anchor not found"
content = content.replace(old, new)
open(path, "w").write(content)
print("Patched")
