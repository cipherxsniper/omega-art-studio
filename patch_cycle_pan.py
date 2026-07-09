path = "/data/data/com.termux/files/home/omega_v10.py"
content = open(path).read()

# ── FIX 1: Treasury cycle — show real balances, no fake updates ──
old1 = '''            cycle_id = str(uuid.uuid4())[:8]
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
            """, (cycle_amount * hops, cycle_amount * hops, wallets[0][0]))'''

new1 = '''            cycle_id = str(uuid.uuid4())[:8]
            hops = 0
            log_lines = []
            total_validated = 0.0
            for w in wallets[:13]:
                wid, wname, bal = w
                real_bal = float(bal or 0)
                total_validated += real_bal
                log_lines.append(
                    f"  ✅ {str(wname or 'Wallet')[:24]}\\n"
                    f"     ${real_bal:>20,.2f}"
                )
                hops += 1'''

assert old1 in content, "FIX1 not found"
content = content.replace(old1, new1)

# ── FIX 2: Treasury cycle output text ────────────────────
old2 = '''                "🔄 *TREASURY CYCLE COMPLETE*\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                f"  Cycle ID:  {cycle_id}\\n"
                f"  Hops:      {hops}\\n"
                f"  Amount:    ${cycle_amount:,.2f} per hop\\n"
                f"  Total:     ${cycle_amount*hops:,.2f} validated\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                + "\\n".join(log_lines) +
                "\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                "  ✅ All funds returned to treasury\\n"
                "  ✅ Cycle recorded on ledger"'''

new2 = '''                "🔄 *WALLET BALANCE SWEEP*\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                f"  Sweep ID:    {cycle_id}\\n"
                f"  Wallets:     {hops}\\n"
                f"  Total Bal:   ${total_validated:,.2f}\\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                + "\\n".join(log_lines) +
                "\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                "  ✅ All balances read from live DB\\n"
                "  ✅ Sweep recorded on ledger"'''

assert old2 in content, "FIX2 not found"
content = content.replace(old2, new2)

# ── FIX 3: Full PAN display at card issue ────────────────
old3 = '''                "  ⚠️ PAN shown once only — save it now"'''
new3 = '''                "  ⚠️ Full PAN shown once only — screenshot now"'''

assert old3 in content, "FIX3 not found"
content = content.replace(old3, new3)

open(path, "w").write(content)
print("All fixes written")
