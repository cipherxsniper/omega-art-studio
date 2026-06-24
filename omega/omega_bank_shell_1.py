#!/usr/bin/env python3

import sqlite3
import uuid
import time
import random
import os
from getpass import getpass

DB = "omega_ledger.db"

SYSTEM_ACCOUNT = "SYSTEM"


class OmegaBankShell:

    def __init__(self):
        self.conn = sqlite3.connect(DB)
        self.conn.row_factory = sqlite3.Row
        self.user = None
        self.account_id = None

    def boot(self):
        os.system("clear")

        print("=" * 60)
        print("🏦 OMEGA BANK")
        print("Autonomous Financial Infrastructure")
        print("=" * 60)

        self.login_loop()

    def login_loop(self):

        while True:

            print("\n1. Login")
            print("2. Create Account")
            print("3. Exit")

            choice = input("\nSelect: ").strip()

            if choice == "1":
                self.login()

            elif choice == "2":
                self.create_account()

            elif choice == "3":
                raise SystemExit

    def create_account(self):

        print("\n=== CREATE ACCOUNT ===")

        username = input("Username: ").strip().upper()
        pin = getpass("4-digit PIN: ").strip()

        routing = str(random.randint(100000000, 999999999))
        account_number = str(random.randint(1000000000, 9999999999))

        wallet_id = str(uuid.uuid4())

        self.conn.execute("""
            INSERT INTO accounts
            VALUES (?, ?, ?)
        """, (
            wallet_id,
            username,
            0.0
        ))

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bank_users (
                username TEXT PRIMARY KEY,
                pin TEXT,
                routing_number TEXT,
                account_number TEXT,
                wallet_id TEXT
            )
        """)

        self.conn.execute("""
            INSERT INTO bank_users
            VALUES (?, ?, ?, ?, ?)
        """, (
            username,
            pin,
            routing,
            account_number,
            wallet_id
        ))

        self.conn.commit()

        print("\n✅ ACCOUNT CREATED")
        print(f"User: {username}")
        print(f"Routing: {routing}")
        print(f"Account: {account_number}")

    def login(self):

        print("\n=== LOGIN ===")

        username = input("Username: ").strip().upper()
        pin = getpass("PIN: ").strip()

        cur = self.conn.cursor()

        cur.execute("""
            SELECT *
            FROM bank_users
            WHERE username=?
            AND pin=?
        """, (username, pin))

        row = cur.fetchone()

        if not row:
            print("\n❌ INVALID LOGIN")
            return

        self.user = username
        self.account_id = username

        print(f"\n🔓 WELCOME {username}")

        self.dashboard()

    def balance(self):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT
            SUM(
                CASE
                    WHEN type='credit' THEN amount
                    WHEN type='debit' THEN -amount
                END
            ) AS balance
            FROM entries
            WHERE account_id=?
        """, (self.account_id,))

        row = cur.fetchone()

        balance = row["balance"]

        if balance is None:
            balance = 0.0

        return round(balance, 2)

    def dashboard(self):

        while True:

            print("\n" + "=" * 60)
            print(f"🏦 OMEGA BANK :: {self.user}")
            print("=" * 60)

            print(f"💰 BALANCE: ${self.balance():,.2f}")

            print("\n1. Send Money")
            print("2. Deposit")
            print("3. View Transactions")
            print("4. Account Details")
            print("5. Logout")

            choice = input("\nSelect: ").strip()

            if choice == "1":
                self.send_money()

            elif choice == "2":
                self.deposit()

            elif choice == "3":
                self.transactions()

            elif choice == "4":
                self.details()

            elif choice == "5":
                self.user = None
                self.account_id = None
                return

    def send_money(self):

        target = input("Recipient Username: ").strip().upper()

        amount = float(input("Amount: $"))

        if self.balance() < amount:
            print("\n❌ INSUFFICIENT FUNDS")
            return

        tx_id = str(uuid.uuid4())

        self.conn.execute("""
            INSERT INTO transactions
            VALUES (?, ?, ?, ?)
        """, (
            tx_id,
            "bank_transfer",
            "posted",
            time.time()
        ))

        self.conn.execute("""
            INSERT INTO entries
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            tx_id,
            self.account_id,
            "debit",
            amount,
            time.time()
        ))

        self.conn.execute("""
            INSERT INTO entries
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            tx_id,
            target,
            "credit",
            amount,
            time.time()
        ))

        self.conn.commit()

        print(f"\n✅ SENT ${amount:,.2f} TO {target}")

    def deposit(self):

        amount = float(input("Deposit Amount: $"))

        tx_id = str(uuid.uuid4())

        self.conn.execute("""
            INSERT INTO transactions
            VALUES (?, ?, ?, ?)
        """, (
            tx_id,
            "external_deposit",
            "posted",
            time.time()
        ))

        self.conn.execute("""
            INSERT INTO entries
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            tx_id,
            SYSTEM_ACCOUNT,
            "debit",
            amount,
            time.time()
        ))

        self.conn.execute("""
            INSERT INTO entries
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            tx_id,
            self.account_id,
            "credit",
            amount,
            time.time()
        ))

        self.conn.commit()

        print(f"\n✅ DEPOSITED ${amount:,.2f}")

    def transactions(self):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT *
            FROM entries
            WHERE account_id=?
            ORDER BY created_at DESC
            LIMIT 10
        """, (self.account_id,))

        rows = cur.fetchall()

        print("\n=== TRANSACTIONS ===\n")

        for row in rows:

            sign = "+"

            if row["type"] == "debit":
                sign = "-"

            print(
                f"{sign}${row['amount']:,.2f} | "
                f"{row['type'].upper()} | "
                f"{row['tx_id']}"
            )

    def details(self):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT *
            FROM bank_users
            WHERE username=?
        """, (self.user,))

        row = cur.fetchone()

        print("\n=== ACCOUNT DETAILS ===")
        print(f"User: {row['username']}")
        print(f"Routing: {row['routing_number']}")
        print(f"Account: {row['account_number']}")


if __name__ == "__main__":

    OmegaBankShell().boot()
