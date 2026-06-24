# =========================================================
# OMEGA ACCOUNT REGISTRY BRIDGE (SINGLE SOURCE MERGER)
# =========================================================

import json
import omega_event_bus_core_v1 as event_bus
import omega_settlement_engine_v1 as settlement

try:
    import omega_wallets
except:
    omega_wallets = None


def load_wallet_accounts():
    try:
        if omega_wallets and hasattr(omega_wallets, "load"):
            return omega_wallets.load()
        if omega_wallets and hasattr(omega_wallets, "wallets"):
            return omega_wallets.wallets
        return {}
    except:
        return {}


def load_settlement_accounts():
    try:
        if hasattr(settlement, "get_snapshot"):
            return settlement.get_snapshot()
        if hasattr(settlement, "settled_balances"):
            return settlement.settled_balances
        return {}
    except:
        return {}


def load_event_history():
    try:
        if hasattr(event_bus, "get_recent_events"):
            return event_bus.get_recent_events(1000)
        return []
    except:
        return []


def build_unified_account_graph():
    wallet_accounts = load_wallet_accounts()
    settlement_accounts = load_settlement_accounts()
    events = load_event_history()

    graph = {
        "wallet_accounts": wallet_accounts,
        "settlement_accounts": settlement_accounts,
        "events": events,
        "users": {}
    }

    return graph


if __name__ == "__main__":
    print(json.dumps(build_unified_account_graph(), indent=2))
