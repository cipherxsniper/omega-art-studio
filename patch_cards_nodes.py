path = "/data/data/com.termux/files/home/omega_v10.py"
content = open(path).read()

# FIX 1: Card list — call get_cards directly from engine
old1 = '''    elif data == "card_list":
        try:
            import psycopg2 as _pg2
            conn = _pg2.connect(host="127.0.0.1", port=5432, dbname="omega_bank",
                                user="postgres", connect_timeout=5)
            cur = conn.cursor()
            cur.execute("""
                SELECT card_token, owner_name, pan_last4, expiry_month, expiry_year,
                       status, spend_limit, spend_used, card_type, issued_at
                FROM omega_cards ORDER BY issued_at DESC
            """)
            rows = cur.fetchall()
            conn.close()
            if not rows:
                text = "💳 No cards issued yet."
            else:
                lines = []
                for c in rows:
                    token, owner, last4, em, ey, status, limit, used, ctype, issued = c
                    icon = "🟢" if status == "ACTIVE" else "🔴"
                    avail = float(limit) - float(used)
                    lines.append(
                        f"{icon} *···· {last4}* | {owner}\\n"
                        f"  Limit: ${float(limit):,.2f} | Used: ${float(used):,.2f} | Avail: ${avail:,.2f}\\n"
                        f"  EXP: {em:02d}/{ey} | {ctype} | {status}"
                    )
                text = "💳 *OMEGA CARDS — LIVE*\\n━━━━━━━━━━━━━━━━━━━━━━\\n\\n" + "\\n\\n".join(lines)
        except Exception as e:
            text = f"❌ Card list error: {e}"
        await query.edit_message_text(text, reply_markup=cards_back, parse_mode="Markdown")'''

new1 = '''    elif data == "card_list":
        try:
            import sys as _sys
            _sys.path.insert(0, "/data/data/com.termux/files/home")
            from omega_card_engine import get_cards as _get_cards, ensure_card_tables as _ect
            _ect()
            rows = _get_cards()
            if not rows:
                text = "💳 No cards issued yet."
            else:
                lines = []
                for c in rows:
                    token, owner, last4, em, ey, status, limit, used, ctype, issued = c[:10]
                    icon = "🟢" if str(status) == "ACTIVE" else "🔴"
                    avail = float(limit) - float(used)
                    lines.append(
                        f"{icon} *···· {last4}* | {owner}\\n"
                        f"  Limit: ${float(limit):,.2f} | Used: ${float(used):,.2f} | Avail: ${avail:,.2f}\\n"
                        f"  EXP: {em:02d}/{ey} | {ctype} | {status}"
                    )
                text = "💳 *OMEGA CARDS — LIVE*\\n━━━━━━━━━━━━━━━━━━━━━━\\n\\n" + "\\n\\n".join(lines)
        except Exception as e:
            text = f"❌ Card list error: {e}"
        await query.edit_message_text(text, reply_markup=cards_back, parse_mode="Markdown")'''

assert old1 in content, "card_list anchor not found"
content = content.replace(old1, new1)

open(path, "w").write(content)
print("Card fix written")
