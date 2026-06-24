#!/usr/bin/env python3
from omega_replay_kernel import ReplayKernel
import psycopg2

"""
CHAOS REPLAY ENGINE
Replays production ledger under stress conditions
"""

def run():
    conn = psycopg2.connect(dbname="omega_bank", user="omega")

    kernel = ReplayKernel(conn)
    state = kernel.replay()

    print("\n[CHAOS REPLAY REPORT]")
    for wallet_id, data in state.items():
        drift = data["balance"]
        print(wallet_id, "RECONSTRUCTED=", drift)

if __name__ == "__main__":
    run()
