#!/usr/bin/env python3

import time
import json
import threading

from omega_cfo_identity_unifier_v1 import build_identity_graph
from omega_ledger_identity_projection_bridge_v1 import project_identity_graph
from omega_cfo_net_worth_engine_v1 import run_net_worth_engine


def merge_views():
    return {
        "identity_graph": build_identity_graph() if "build_identity_graph" in globals() else {},
        "ledger_projection": project_identity_graph(),
        "net_worth": run_net_worth_engine()
    }


def render_dashboard(snapshot):
    print("\n🧠 OMEGA REAL-TIME CFO DASHBOARD")
    print("=" * 60)

    net = snapshot["net_worth"]

    print(f"📊 SYSTEM STATUS: {net['status']}")
    print(f"⏱ TIMESTAMP: {net['timestamp']}")
    print(f"\n💰 TOTAL SYSTEM VALUE: {net['total_system_value']:.2f}\n")

    print("📒 BALANCES:")
    for k, v in net["balances"].items():
        print(f"  {k}: {v:.2f}")

    print("\n🔁 LIVE MODE: REFRESHING EVERY 5s (CTRL+C to stop)\n")


def live_loop():
    while True:
        snapshot = merge_views()
        render_dashboard(snapshot)
        time.sleep(5)


if __name__ == "__main__":
    try:
        live_loop()
    except KeyboardInterrupt:
        print("\n🛑 CFO DASHBOARD STOPPED")
