# ================================
# OMEGA BANK CLI (REAL LEDGER VIEW)
# ================================

from event_ledger_engine import get_ledger_snapshot


def run_bank():
    data = get_ledger_snapshot()

    print("\n🏦 OMEGA BANK — LIVE LEDGER VIEW\n")

    accounts = data.get("accounts", [])
    total = data.get("total_balance", 0)
    events = data.get("event_count", 0)

    if not accounts:
        print("⚠️ No accounts found in ledger projection.")
        print("Run ledger rebuild / ensure accounts table is populated.\n")
        return

    for acc in accounts:
        print("┌──────────────────────────────────────────────┐")
        print(f"│ ACCOUNT : {acc['account_id']}")
        print(f"│ BALANCE : ${acc['balance']:,.2f} USD")
        print("└──────────────────────────────────────────────┘\n")

    print("══════════════════════════════════════════════")
    print(f"💰 TOTAL SYSTEM BALANCE: ${total:,.2f} USD")
    print(f"📒 EVENT COUNT: {events}")
    print("══════════════════════════════════════════════\n")


if __name__ == "__main__":
    run_bank()
