#!/usr/bin/env python3
import os

BASE = os.path.dirname(__file__)

DBS = {
    "ledger": os.path.join(BASE, "omega_ledger.db"),
    "billing": os.path.join(BASE, "billing.db"),
    "bank": os.path.join(BASE, "omega_bank.db"),
    "users": os.path.join(BASE, "omega_users.db"),
    "queue": os.path.join(BASE, "event_queue.db"),
    "idempotency": os.path.join(BASE, "idempotency.db"),
    "external": os.path.join(BASE, "external_accounts.db"),
}

def get_db(name: str):
    if name not in DBS:
        raise ValueError(f"Unknown DB: {name}")
    return DBS[name]

def print_map():
    print("=== OMEGA DB REGISTRY ===")
    for k, v in DBS.items():
        print(f"{k:15} -> {v}")

if __name__ == "__main__":
    print_map()
