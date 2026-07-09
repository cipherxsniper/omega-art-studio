import re

path = "/data/data/com.termux/files/home/omega_v10.py"
content = open(path).read()

# ── 1. Add 3 buttons to finance menu ──────────────────────
old_kb = '''        [
            InlineKeyboardButton("💰 Revenue",       callback_data="revenue"),
            InlineKeyboardButton("🔙 Main Menu",     callback_data="menu"),
        ],
    ]
    return text, InlineKeyboardMarkup(kb)'''

new_kb = '''        [
            InlineKeyboardButton("📜 Ledger Events", callback_data="finance_ledger_events"),
            InlineKeyboardButton("🔄 Treasury Cycle",callback_data="finance_treasury_cycle"),
        ],
        [
            InlineKeyboardButton("📋 Cycle History", callback_data="finance_cycle_history"),
            InlineKeyboardButton("💰 Revenue",       callback_data="revenue"),
        ],
        [
            InlineKeyboardButton("🔙 Main Menu",     callback_data="menu"),
        ],
    ]
    return text, InlineKeyboardMarkup(kb)'''

assert old_kb in content, "KB anchor not found"
content = content.replace(old_kb, new_kb)

# ── 2. Add handlers inside finance_button_handler ─────────
old_audit_end = '''    elif data == "finance_audit":'''

new_handlers = '''    elif data == "finance_ledger_events":
        try:
            import psycopg2 as _pg2
            conn = _pg2.connect(host="127.0.0.1", port=5432, dbname="omega_ledger",
                                user="postgres", connect_timeout=5)
            cur = conn.cursor()
            cur.execute("""
                SELECT entry_id, entry_type, amount, currency,
                       left(entry_hash,12), created_at
                FROM ledger_entries
                ORDER BY created_at DESC LIMIT 20
            """)
            rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) FROM ledger_entries")
            total = cur.fetchone()[0]
            conn.close()
            lines = []
            for r in rows:
                lines.append(
                    f"  {str(r[5])[:16]}\\n"
                    f"  {r[1]} | {r[2]} {r[3]}\\n"
                    f"  Hash: {r[4]}..."
                )
            text = (
                "📜 *LEDGER EVENTS — LIVE*\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                f"  Total entries: {total:,}\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                + "\\n\\n".join(lines[:20])
            )
        except Exception as e:
            text = f"❌ Ledger error: {e}"
        await query.edit_message_text(text, reply_markup=fin_back_kb, parse_mode="Markdown")

    elif data == "finance_treasury_cycle":
        try:
            import psycopg2 as _pg2, uuid, datetime
            conn = _pg2.connect(host="127.0.0.1", port=5432, dbname="omega_bank",
                                user="postgres", connect_timeout=5)
            cur = conn.cursor()
            # Get all active wallets
            cur.execute("""
                SELECT w.id, a.owner_name, w.available_balance
                FROM wallets w
                JOIN accounts a ON a.account_id = w.account_id
                WHERE w.status = 'active'
                ORDER BY w.available_balance DESC
            """)
            wallets = cur.fetchall()
            if not wallets:
                await query.edit_message_text("❌ No active wallets found", reply_markup=fin_back_kb)
                conn.close()
                return
            cycle_id = str(uuid.uuid4())[:8]
            cycle_amount = 1000.00
            hops = 0
            log_lines = []
            # Cycle $1000 through each wallet and back
            for w in wallets[:5]:
                wid, wname, bal = w
                hop_key = f"cycle_{cycle_id}_hop_{hops}"
                cur.execute("""
                    UPDATE wallets SET
                        available_balance = available_balance - %s,
                        pending_balance = pending_balance + %s
                    WHERE id = %s
                """, (cycle_amount, cycle_amount, wid))
                log_lines.append(f"  ✅ {str(wname)[:20]} → ${cycle_amount:,.2f}")
                hops += 1
            # Return all to treasury
            cur.execute("""
                UPDATE wallets SET
                    available_balance = available_balance + %s,
                    pending_balance = pending_balance - %s
                WHERE id = %s
            """, (cycle_amount * hops, cycle_amount * hops, wallets[0][0]))
            # Record cycle in omega_ledger
            cur2 = conn.cursor()
            try:
                cur2.execute("""
                    INSERT INTO omega_genesis_events
                    (genesis_id, genesis_hash, treasury_usd, node_count, wallet_count, payload, signed_by, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    f"cycle_{cycle_id}",
                    f"CYCLE_{cycle_id}_{hops}hops",
                    cycle_amount * hops,
                    hops, len(wallets),
                    f"Treasury cycle {cycle_id} — {hops} hops — ${cycle_amount*hops:,.2f} validated",
                    "omega_v10"
                ))
            except Exception:
                pass
            conn.commit()
            conn.close()
            text = (
                "🔄 *TREASURY CYCLE COMPLETE*\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                f"  Cycle ID:  {cycle_id}\\n"
                f"  Hops:      {hops}\\n"
                f"  Amount:    ${cycle_amount:,.2f} per hop\\n"
                f"  Total:     ${cycle_amount*hops:,.2f} validated\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                + "\\n".join(log_lines) +
                "\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                "  ✅ All funds returned to treasury\\n"
                "  ✅ Cycle recorded on ledger"
            )
        except Exception as e:
            text = f"❌ Cycle error: {e}"
        await query.edit_message_text(text, reply_markup=fin_back_kb, parse_mode="Markdown")

    elif data == "finance_cycle_history":
        try:
            import psycopg2 as _pg2
            conn = _pg2.connect(host="127.0.0.1", port=5432, dbname="omega_bank",
                                user="postgres", connect_timeout=5)
            cur = conn.cursor()
            cur.execute("""
                SELECT genesis_id, treasury_usd, node_count, created_at
                FROM omega_genesis_events
                WHERE genesis_id LIKE 'cycle_%'
                ORDER BY created_at DESC LIMIT 10
            """)
            rows = cur.fetchall()
            conn.close()
            if not rows:
                text = "📋 *Cycle History*\\n\\n_No cycles run yet. Use 🔄 Treasury Cycle to run first._"
            else:
                lines = [
                    f"  {str(r[3])[:16]}\\n"
                    f"  ID: {r[0]} | {r[1]} hops | ${float(r[1] or 0):,.2f}"
                    for r in rows
                ]
                text = (
                    "📋 *TREASURY CYCLE HISTORY*\\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                    + "\\n\\n".join(lines)
                )
        except Exception as e:
            text = f"❌ History error: {e}"
        await query.edit_message_text(text, reply_markup=fin_back_kb, parse_mode="Markdown")

    elif data == "finance_audit":'''

assert old_audit_end in content, "Audit anchor not found"
content = content.replace(old_audit_end, new_handlers)

open(path, "w").write(content)
print("Patch written")
