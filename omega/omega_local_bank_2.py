#!/usr/bin/env python3

import json
import os
import uuid
from datetime import datetime

DB_FILE = "omega_accounts.json"

ACCOUNTS = ["omega_credit", "omega_revenue", "omega_investment", "omega_personal"]

# ----------------------------
# LOAD / SAVE
# ----------------------------
def load():
    if not os.path.exists(DB_FILE):
        return None
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ----------------------------
# INIT USER
# ----------------------------
def create_user():
    print("\n=== OMEGA BANK SETUP ===")
    username = input("Create username: ")
    pin = input("Create PIN: ")

    user = {
        "username": username,
        "pin": pin,
        "wallet_address": str(uuid.uuid4()),
        "accounts": {
            name: {"balance": 0.0, "ledger": []}
            for name in ACCOUNTS
        },
        "created_at": str(datetime.utcnow())
    }

    save(user)
    print("\nACCOUNT CREATED")
    print("Wallet:", user["wallet_address"])
    return user

# ----------------------------
# LOGIN
# ----------------------------
def login(data):
    print("\n=== LOGIN ===")
    pin = input("Enter PIN: ")
    if pin == data["pin"]:
        print("ACCESS GRANTED\n")
        return True
    print("DENIED\n")
    return False

# ----------------------------
# LEDGER ENTRY
# ----------------------------
def log_tx(account, amount, note):
    entry = {
        "time": str(datetime.utcnow()),
        "amount": amount,
        "note": note
    }
    account["ledger"].append(entry)

# ----------------------------
# TRANSFER ENGINE
# ----------------------------
def transfer(data, src, dst, amount):
    if data["accounts"][src]["balance"] < amount:
        print("INSUFFICIENT FUNDS")
        return

    data["accounts"][src]["balance"] -= amount
    data["accounts"][dst]["balance"] += amount

    log_tx(data["accounts"][src], -amount, f"sent to {dst}")
    log_tx(data["accounts"][dst], amount, f"received from {src}")

    save(data)
    print("TRANSFER COMPLETE")

# ----------------------------
# VIEW BALANCES
# ----------------------------
def show(data):
    print("\n=== BALANCES ===")
    for k, v in data["accounts"].items():
        print(k, ":", v["balance"])

# ----------------------------
# MAIN LOOP
# ----------------------------
def run():
    data = load()

    if not data:
        data = create_user()

    if not login(data):
        return

    while True:
        print("\n1) View balances")
        print("2) Add funds")
        print("3) Transfer")
        print("4) Exit")

        choice = input("> ")

        if choice == "1":
            show(data)

        elif choice == "2":
            acc = input("Account: ")
            amt = float(input("Amount: "))
            data["accounts"][acc]["balance"] += amt
            log_tx(data["accounts"][acc], amt, "deposit")
            save(data)

        elif choice == "3":
            src = input("From: ")
            dst = input("To: ")
            amt = float(input("Amount: "))
            transfer(data, src, dst, amt)

        elif choice == "4":
            break

if __name__ == "__main__":
    run()
