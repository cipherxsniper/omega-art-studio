path = "/data/data/com.termux/files/home/omega_oracle_v2.py"
content = open(path).read()

old = '''    if name == "omega_sentinel":'''

new = '''    # Functional tests — verify real data flows not just syntax
    if name == "omega_v10":
        # Test 1: card engine returns real data
        try:
            import sys as _sys
            _sys.path.insert(0, str(HOME))
            from omega_card_engine import get_cards, ensure_card_tables
            ensure_card_tables()
            cards = get_cards()
            if len(cards) == 0:
                score -= 5
                issues.append("functional: card engine returns no cards")
        except Exception as e:
            score -= 5
            issues.append(f"functional: card engine error: {e}")

        # Test 2: ledger DB has real entries
        try:
            import psycopg2
            conn = psycopg2.connect(host="127.0.0.1", port=5432,
                                    dbname="omega_ledger", user="postgres",
                                    connect_timeout=3)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ledger_entries")
            count = cur.fetchone()[0]
            conn.close()
            if count == 0:
                score -= 5
                issues.append("functional: ledger has 0 entries")
        except Exception as e:
            score -= 5
            issues.append(f"functional: ledger entries error: {e}")

        # Test 3: wallet data is real
        try:
            import psycopg2
            conn = psycopg2.connect(host="127.0.0.1", port=5432,
                                    dbname="omega_bank", user="postgres",
                                    connect_timeout=3)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM wallets WHERE available_balance > 0")
            wct = cur.fetchone()[0]
            conn.close()
            if wct == 0:
                score -= 5
                issues.append("functional: no wallets with balance")
        except Exception as e:
            score -= 5
            issues.append(f"functional: wallet check error: {e}")

    if name == "omega_sentinel":'''

assert old in content, "anchor not found"
content = content.replace(old, new)
open(path, "w").write(content)
print("Oracle functional tests added")
