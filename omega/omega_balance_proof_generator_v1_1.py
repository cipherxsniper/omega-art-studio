import sqlite3
import json
from collections import defaultdict
from decimal import Decimal

DB = "omega_ledger.db"

def parse_payload(payload):
    if isinstance(payload, str):
        return json.loads(payload)
    return payload

def compute_balances(events):
    balances = defaultdict(Decimal)

    for event_id, event_type, payload, timestamp in events:
        payload = parse_payload(payload)

        sender = payload.get("sender_wallet")
        receiver = payload.get("receiver_wallet")
        amount = Decimal(str(payload.get("amount", 0)))

        # debit
        if sender:
            balances[sender] -= amount

        # credit
        if receiver:
            balances[receiver] += amount

    return balances

def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT id, type, payload, timestamp FROM events ORDER BY rowid ASC")
    events = cur.fetchall()

    balances = compute_balances(events)

    print("🧮 BALANCE PROOF GENERATED")
    for wallet, balance in balances.items():
        print(wallet, float(balance))

    conn.close()

if __name__ == "__main__":
    run()
