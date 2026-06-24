#!/usr/bin/env python3

import omega_event_bus_core_v1 as event_bus


def seed_core_accounts():
    genesis_events = [
        {
            "event_type": "SETTLEMENT_EVENT",
            "currency": "USD",
            "ledger_effect": {
                "OMEGA_TREASURY": 6500000000.0,
                "OMEGA_RESERVE": 6000000000.0,
                "OMEGA_INVESTMENT": 750000000.0,
                "OMEGA_CREDIT": 500000000.0,
                "THOMAS_LH": 50000000.0
            }
        }
    ]

    for e in genesis_events:
        event_bus.insert_event(e)

    return "GENESIS_SEED_COMPLETE"


if __name__ == "__main__":
    print(seed_core_accounts())
