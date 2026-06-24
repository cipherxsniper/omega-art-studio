#!/usr/bin/env python3

import sqlite3
import omega_event_bus_core_v1 as event_bus

DB_PATH = event_bus.DB_PATH


def seed():

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    event_bus.ensure_schema(cur)

    events = [
        {
            "event_type": "SETTLEMENT_EVENT",
            "currency": "USD",
            "ledger_effect": {"OMEGA_TREASURY": 6500000000.0}
        },
        {
            "event_type": "SETTLEMENT_EVENT",
            "currency": "USD",
            "ledger_effect": {"OMEGA_RESERVE": 6000000000.0}
        },
        {
            "event_type": "SETTLEMENT_EVENT",
            "currency": "USD",
            "ledger_effect": {"OMEGA_INVESTMENT": 750000000.0}
        },
        {
            "event_type": "SETTLEMENT_EVENT",
            "currency": "USD",
            "ledger_effect": {"OMEGA_CREDIT": 500000000.0}
        },
        {
            "event_type": "SETTLEMENT_EVENT",
            "currency": "USD",
            "ledger_effect": {"THOMAS_LH": 50000000.0}
        }
    ]

    for e in events:
        event_bus.insert_event(cur, e)

    conn.commit()
    conn.close()

    print("GENESIS COMPLETE — LEDGER INITIALIZED")


if __name__ == "__main__":
    seed()
