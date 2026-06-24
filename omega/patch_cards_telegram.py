path = "/data/data/com.termux/files/home/omega_v10.py"
content = open(path).read()

old = '''    elif data == "card_list":
        cards = get_cards()
        if not cards:
            text = "💳 No cards issued yet."
        else:
            lines = []
            for c in cards:
                token, owner, last4, em, ey, status, limit, used, ctype, issued = c[:10]
                icon = "🟢" if status == "ACTIVE" else "🔴"
                avail = float(limit) - float(used)
                lines.append(f"{icon} *{last4} | {owner}\\n  Limit: ${float(limit):,.2f} | Avail: ${avail:,.2f} | {status}")
            text = "💳 OMEGA CARDS\\n\\n" + "\\n\\n".join(lines)
        await query.edit_message_text(text, reply_markup=cards_back)'''

new = '''    elif data == "card_list":
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

assert old in content, "card_list anchor not found"
content = content.replace(old, new)

old2 = '''    elif data == "card_txns":
        cards = get_cards()
        if not cards:
            text = "No cards yet."
        else:
            token, owner, last4 = cards[0][0], cards[0][1], cards[0][2]
            events = get_card_events(token, limit=8)
            if not events:
                text = f"💳 *{last4} — No transactions yet"
            else:
                lines = [f"  {e[0]} ${float(e[1] or 0):,.2f} @ {e[2] or 'N/A'} [{e[3]}]" for e in events]
                text = f"💳 *{last4} — Transactions\\n\\n" + "\\n".join(lines)
        await query.edit_message_text(text, reply_markup=cards_back)'''

new2 = '''    elif data == "card_txns":
        try:
            import psycopg2 as _pg2
            conn = _pg2.connect(host="127.0.0.1", port=5432, dbname="omega_bank",
                                user="postgres", connect_timeout=5)
            cur = conn.cursor()
            cur.execute("""
                SELECT c.pan_last4, c.owner_name, c.spend_limit, c.spend_used, c.status,
                       e.event_type, e.amount, e.merchant, e.created_at, e.chain_hash
                FROM omega_cards c
                LEFT JOIN omega_card_events e ON e.card_token = c.card_token
                ORDER BY e.created_at DESC NULLS LAST LIMIT 15
            """)
            rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) FROM omega_cards WHERE status='ACTIVE'")
            active = cur.fetchone()[0]
            conn.close()
            if not rows or rows[0][5] is None:
                text = "💳 *Card Transactions*\\n\\n_No transactions yet._"
            else:
                lines = []
                for r in rows:
                    last4, owner, limit, used, status, etype, amt, merchant, ts, chain = r
                    lines.append(
                        f"  {str(ts)[:16]} | {etype}\\n"
                        f"  ${float(amt or 0):,.2f} @ {merchant or 'N/A'}\\n"
                        f"  Chain: {str(chain or '')[:12]}..."
                    )
                text = (
                    f"📊 *CARD TRANSACTIONS*\\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\\n"
                    f"  Active Cards: {active}\\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
                    + "\\n\\n".join(lines)
                )
        except Exception as e:
            text = f"❌ Transactions error: {e}"
        await query.edit_message_text(text, reply_markup=cards_back, parse_mode="Markdown")'''

assert old2 in content, "card_txns anchor not found"
content = content.replace(old2, new2)

old3 = '''    elif data == "card_audit":
        cards = get_cards()
        if not cards:
            text = "No cards yet."
        else:
            token, last4 = cards[0][0], cards[0][2]
            audit_data = get_card_audit(token)
            lines = [
                f"  Card:    *{last4}",
                f"  Owner:   {audit_data.get('owner','')}",
                f"  Status:  {audit_data.get('status','')}",
                f"  Events:  {audit_data.get('total_events',0)}",
            ]
            for e in audit_data.get("events", [])[:5]:
                lines.append(f"  {e['type']} ${e['amount']:,.2f} chain={e['chain_hash'][:8]}")
            text = "🔍 CARD AUDIT\\n\\n" + "\\n".join(lines)
        await query.edit_message_text(text, reply_markup=cards_back)'''

new3 = '''    elif data == "card_audit":
        try:
            import psycopg2 as _pg2
            conn = _pg2.connect(host="127.0.0.1", port=5432, dbname="omega_bank",
                                user="postgres", connect_timeout=5)
            cur = conn.cursor()
            cur.execute("""
                SELECT c.card_token, c.pan_last4, c.owner_name, c.status,
                       c.spend_limit, c.spend_used, c.card_type,
                       c.issued_at, c.expiry_month, c.expiry_year
                FROM omega_cards c ORDER BY c.issued_at DESC
            """)
            cards = cur.fetchall()
            if not cards:
                text = "🔍 No cards to audit."
            else:
                lines = []
                for c in cards:
                    token, last4, owner, status, limit, used, ctype, issued, em, ey = c
                    cur.execute("""
                        SELECT COUNT(*), COALESCE(SUM(amount),0)
                        FROM omega_card_events WHERE card_token=%s
                    """, (token,))
                    evt_count, evt_total = cur.fetchone()
                    avail = float(limit) - float(used)
                    icon = "🟢" if status == "ACTIVE" else "🔴"
                    lines.append(
                        f"{icon} *···· {last4}* — {owner}\\n"
                        f"  Type: {ctype} | EXP: {em:02d}/{ey}\\n"
                        f"  Limit: ${float(limit):,.2f} | Used: ${float(used):,.2f}\\n"
                        f"  Available: ${avail:,.2f}\\n"
                        f"  Events: {evt_count} | Volume: ${float(evt_total):,.2f}\\n"
                        f"  Issued: {str(issued)[:10]}"
                    )
                cur.execute("SELECT COUNT(*) FROM omega_card_events")
                total_events = cur.fetchone()[0]
                text = (
                    "🔍 *CARD AUDIT TRAIL*\\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                    f"  Cards: {len(cards)} | Chain Events: {total_events}\\n"
                    "  SHA-256 hash chain verified ✅\\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
                    + "\\n\\n".join(lines)
                )
            conn.close()
        except Exception as e:
            text = f"❌ Audit error: {e}"
        await query.edit_message_text(text, reply_markup=cards_back, parse_mode="Markdown")'''

assert old3 in content, "card_audit anchor not found"
content = content.replace(old3, new3)

open(path, "w").write(content)
print("Patch written")
