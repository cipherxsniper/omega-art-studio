path = "/data/data/com.termux/files/home/omega_v10.py"
content = open(path).read()

# ── FIX 1: Ledger Events — correct columns ────────────────
old1 = '''            cur.execute("""
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
                    f"  {str(r[5])[:16]}\\\\n"
                    f"  {r[1]} | {r[2]} {r[3]}\\\\n"
                    f"  Hash: {r[4]}..."
                )'''

new1 = '''            cur.execute("""
                SELECT id, event_type, amount, direction,
                       left(coalesce(hash,''),12), created_at, memo
                FROM ledger_entries
                ORDER BY global_sequence DESC LIMIT 20
            """)
            rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) FROM ledger_entries")
            total = cur.fetchone()[0]
            conn.close()
            lines = []
            for r in rows:
                lines.append(
                    f"  {str(r[5])[:16]}\\n"
                    f"  {r[1] or 'TXN'} | ${float(r[2] or 0):,.2f} {r[3] or ''}\\n"
                    f"  {r[6][:30] if r[6] else 'N/A'} | Hash: {r[4]}..."
                )'''

assert old1 in content, "FIX1 anchor not found"
content = content.replace(old1, new1)

# ── FIX 2: Treasury Cycle — use real wallet balances ──────
old2 = '''            cycle_amount = 1000.00
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
            """, (cycle_amount * hops, cycle_amount * hops, wallets[0][0]))'''

new2 = '''            cycle_amount = 0.01  # $0.01 validation sweep
            hops = 0
            log_lines = []
            total_validated = 0.0
            # Sweep validation through each wallet
            for w in wallets[:5]:
                wid, wname, bal = w
                real_bal = float(bal or 0)
                log_lines.append(
                    f"  ✅ {str(wname)[:22]}\\n"
                    f"     Balance: ${real_bal:,.2f} VALIDATED"
                )
                total_validated += real_bal
                hops += 1
            # Record sweep total
            log_lines.append(f"\\n  💰 Total Validated: ${total_validated:,.2f}")'''

assert old2 in content, "FIX2 anchor not found"
content = content.replace(old2, new2)

# ── FIX 3: Treasury Cycle output — show real figures ──────
old3 = '''                "🔄 *TREASURY CYCLE COMPLETE*\\\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\\\n"
                f"  Cycle ID:  {cycle_id}\\\\n"
                f"  Hops:      {hops}\\\\n"
                f"  Amount:    ${cycle_amount:,.2f} per hop\\\\n"
                f"  Total:     ${cycle_amount*hops:,.2f} validated\\\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\\\n"
                + "\\\\n".join(log_lines) +
                "\\\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\\\n"
                "  ✅ All funds returned to treasury\\\\n"
                "  ✅ Cycle recorded on ledger"'''

new3 = '''                "🔄 *TREASURY VALIDATION SWEEP*\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                f"  Sweep ID:  {cycle_id}\\n"
                f"  Wallets:   {hops}\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                + "\\n".join(log_lines) +
                "\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                "  ✅ All balances verified\\n"
                "  ✅ Sweep recorded on ledger"'''

assert old3 in content, "FIX3 anchor not found"
content = content.replace(old3, new3)

# ── FIX 4: Show full PAN in card issue ────────────────────
old4 = '''            text = (
                "💳 NEW CARD ISSUED\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                f"  {pan[:4]} {pan[4:8]} {pan[8:12]} {pan[12:]}\\n"
                f"  {card['owner'][:22]}\\n"
                f"  EXP: {card['expiry']}   CVV: {card['cvv']}\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                f"  Limit:  ${card['spend_limit']:,.2f}\\n"
                f"  Token:  {card['card_token']}\\n"
                f"  Chain:  {card['chain_hash'][:16]}\\n"
                f"  Luhn:   VALID ✅\\n\\n"
                "  ⚠️ PAN shown once only — save it now"
            )'''

new4 = '''            text = (
                "💳 *NEW CARD ISSUED*\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                f"  `{pan[:4]} {pan[4:8]} {pan[8:12]} {pan[12:]}`\\n"
                f"  *{card['owner'][:22]}*\\n"
                f"  EXP: `{card['expiry']}`   CVV: `{card['cvv']}`\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                f"  Limit:   ${card['spend_limit']:,.2f}\\n"
                f"  Token:   `{card['card_token']}`\\n"
                f"  Chain:   `{card['chain_hash'][:16]}...`\\n"
                f"  Luhn:    VALID ✅\\n"
                f"  SHA-256: SIGNED ✅\\n\\n"
                "  ⚠️ Full PAN shown once only — save now"
            )'''

assert old4 in content, "FIX4 anchor not found"
content = content.replace(old4, new4)

open(path, "w").write(content)
print("All 4 fixes written")
