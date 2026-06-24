import random
import uuid
import time
from datetime import datetime
from omega_env_bootstrap_v1 import bootstrap_env

ENV = bootstrap_env()

ACCOUNTS = [
    "OMEGA_TREASURY",
    "OMEGA_CREDIT",
    "OMEGA_RESERVE",
    "OMEGA_INVESTMENT",
    "THOMAS_LH"
]

def generate_transaction():
    from_acct = random.choice(ACCOUNTS)
    to_acct = random.choice([a for a in ACCOUNTS if a != from_acct])

    amount = round(random.uniform(0.01, 50000.00), 2)

    return {
        "tx_id": str(uuid.uuid4()),
        "from": from_acct,
        "to": to_acct,
        "amount": amount,
        "currency": "USD",
        "timestamp": datetime.utcnow().isoformat()
    }

def run_chaos(n=100000):
    print("🧪 OMEGA CHAOS TEST STARTING")

    for i in range(n):
        tx = generate_transaction()

        if i % 10000 == 0:
            print(f"Injected {i} transactions... sample:", tx)

    print("✅ CHAOS TEST COMPLETE — 100,000 TRANSACTIONS INJECTED")

if __name__ == "__main__":
    run_chaos()
