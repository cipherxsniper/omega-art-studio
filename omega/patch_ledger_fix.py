path = "/data/data/com.termux/files/home/omega_v10.py"
content = open(path).read()

old = '''            cur.execute("""
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
                )'''

new = '''            cur.execute("""
                SELECT id, event_type, amount, direction,
                       left(coalesce(hash,'none'),12), created_at, memo
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
                    f"  {(r[6] or 'N/A')[:30]} | Hash: {r[4]}..."
                )'''

if old in content:
    content = content.replace(old, new)
    open(path, "w").write(content)
    print("Patched")
else:
    # Show what's actually there
    idx = content.find("finance_ledger_events")
    print("Current text around ledger_events:")
    print(repr(content[idx:idx+500]))
