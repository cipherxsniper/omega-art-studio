from omega_balance_bridge import get_real_balances

def show_real_balances():
    rows = get_real_balances()

    print("\n=== OMEGA BANK LIVE LEDGER BALANCES ===")
    for r in rows:
        wallet_id, settled, ledger, drift = r
        print(f"""
wallet:   {wallet_id}
settled:  {settled}
ledger:   {ledger}
drift:    {drift}
-------------------------
""")
