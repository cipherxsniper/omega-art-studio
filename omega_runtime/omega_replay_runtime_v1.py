#!/usr/bin/env python3

import os
import json
import hashlib
import psycopg2
from decimal import Decimal
from collections import defaultdict

DB_NAME = "omega_bank"
DB_USER = "omega"
DB_PASSWORD = os.getenv("OMEGA_DB_PASSWORD", "")
DB_HOST = "localhost"
DB_PORT = "5432"


class OmegaReplayRuntime:

    def __init__(self):
        self.wallet_balances = defaultdict(Decimal)
        self.wallet_reserved = defaultdict(Decimal)

        self.merchant_balances = defaultdict(Decimal)

        self.treasury_liabilities = Decimal("0")
        self.treasury_cash = Decimal("0")

        self.active_holds = {}

        self.event_chain_hash = ""
        self.global_state_hash = ""

    def get_connection(self):
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn

    def append_hash(self, previous_hash, payload):
        raw = f"{previous_hash}:{payload}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def load_events(self):

        conn = self.get_connection()

        try:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT
                        event_id,
                        event_type,
                        payload,
                        created_at
                    FROM omega_events
                    ORDER BY created_at ASC
                """)

                rows = cur.fetchall()

                events = []

                for row in rows:

                    payload = row[3]

                    if isinstance(payload, str):
                        payload = json.loads(payload)

                    events.append({
                        "event_id": str(row[0]),
                        "event_type": row[1],
                        "entity_id": str(row[2]),
                        "payload": payload,
                        "created_at": str(row[4])
                    })

                return events

        finally:
            conn.close()

    def apply_auth_created(self, event):

        payload = event["payload"]

        auth_id = payload["auth_id"]

        wallet_id = payload["wallet_id"]

        amount = Decimal(str(payload["amount"]))

        self.wallet_reserved[wallet_id] += amount

        self.active_holds[auth_id] = {
            "wallet_id": wallet_id,
            "amount": amount,
            "state": "ACTIVE"
        }

    def apply_auth_captured(self, event):

        payload = event["payload"]

        auth_id = payload["auth_id"]

        capture_amount = Decimal(str(payload["amount"]))

        if auth_id not in self.active_holds:
            raise Exception(f"Missing auth hold: {auth_id}")

        hold = self.active_holds[auth_id]

        wallet_id = hold["wallet_id"]

        self.wallet_reserved[wallet_id] -= capture_amount

        self.wallet_balances[wallet_id] -= capture_amount

        merchant_id = payload["merchant_id"]

        self.merchant_balances[merchant_id] += capture_amount

        self.treasury_liabilities -= capture_amount

        self.treasury_cash -= capture_amount

        remaining = hold["amount"] - capture_amount

        hold["amount"] = remaining

        if remaining <= Decimal("0"):
            hold["state"] = "CAPTURED"

    def apply_auth_reversed(self, event):

        payload = event["payload"]

        auth_id = payload["auth_id"]

        if auth_id not in self.active_holds:
            return

        hold = self.active_holds[auth_id]

        wallet_id = hold["wallet_id"]

        amount = hold["amount"]

        self.wallet_reserved[wallet_id] -= amount

        hold["amount"] = Decimal("0")

        hold["state"] = "REVERSED"

    def apply_auth_expired(self, event):

        payload = event["payload"]

        auth_id = payload["auth_id"]

        if auth_id not in self.active_holds:
            return

        hold = self.active_holds[auth_id]

        wallet_id = hold["wallet_id"]

        amount = hold["amount"]

        self.wallet_reserved[wallet_id] -= amount

        hold["amount"] = Decimal("0")

        hold["state"] = "EXPIRED"

    def process_event(self, event):

        payload_json = json.dumps(
            event,
            sort_keys=True
        )

        self.event_chain_hash = self.append_hash(
            self.event_chain_hash,
            payload_json
        )

        event_type = event["event_type"]

        if event_type == "AUTH_CREATED":
            self.apply_auth_created(event)

        elif event_type == "AUTH_CAPTURED":
            self.apply_auth_captured(event)

        elif event_type == "AUTH_REVERSED":
            self.apply_auth_reversed(event)

        elif event_type == "AUTH_EXPIRED":
            self.apply_auth_expired(event)

    def compute_state_hash(self):

        state = {
            "wallet_balances": {
                k: str(v)
                for k, v in self.wallet_balances.items()
            },
            "wallet_reserved": {
                k: str(v)
                for k, v in self.wallet_reserved.items()
            },
            "merchant_balances": {
                k: str(v)
                for k, v in self.merchant_balances.items()
            },
            "treasury_liabilities": str(self.treasury_liabilities),
            "treasury_cash": str(self.treasury_cash),
            "active_holds": {
                k: {
                    "wallet_id": v["wallet_id"],
                    "amount": str(v["amount"]),
                    "state": v["state"]
                }
                for k, v in self.active_holds.items()
            }
        }

        raw = json.dumps(
            state,
            sort_keys=True
        )

        self.global_state_hash = hashlib.sha256(
            raw.encode()
        ).hexdigest()

    def verify_invariants(self):

        debit_total = Decimal("0")
        credit_total = Decimal("0")

        for value in self.wallet_balances.values():
            debit_total += value

        for value in self.merchant_balances.values():
            credit_total += value

        if abs(debit_total) != abs(credit_total):
            raise Exception(
                f"DOUBLE ENTRY VIOLATION: debits={debit_total} credits={credit_total}"
            )

        reserved_total = Decimal("0")

        for hold in self.active_holds.values():

            if hold["state"] == "ACTIVE":
                reserved_total += hold["amount"]

        wallet_reserved_total = sum(
            self.wallet_reserved.values(),
            Decimal("0")
        )

        if reserved_total != wallet_reserved_total:
            raise Exception(
                "AUTH HOLD INVARIANT FAILURE"
            )

    def replay(self):

        print("Loading events...")

        events = self.load_events()

        print(f"Loaded {len(events)} events")

        for event in events:
            self.process_event(event)

        self.verify_invariants()

        self.compute_state_hash()

        print("")
        print("===== REPLAY COMPLETE =====")
        print(f"EVENT CHAIN HASH : {self.event_chain_hash}")
        print(f"STATE HASH       : {self.global_state_hash}")
        print("Replay deterministic and verified.")
        print("")


def main():

    runtime = OmegaReplayRuntime()

    runtime.replay()


if __name__ == "__main__":
    main()
