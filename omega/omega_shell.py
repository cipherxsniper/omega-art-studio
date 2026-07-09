from core.identity import Identity
from database.db import SessionLocal
from sqlalchemy import text

identity = Identity()

def setup():
    print("\n=== OMEGA BANK SETUP ===")

    name = input("Enter name: ")
    pin = input("Create 4-digit PIN: ")
    confirm = input("Confirm PIN: ")

    if pin != confirm:
        print("PIN mismatch")
        return setup()

    profile = identity.create(name, pin)

    print("\nAccount created")
    print("User ID:", profile["user_id"])

def login():
    pin = input("Enter PIN: ")

    if not identity.verify_pin(pin):
        print("Access denied")
        return False

    return True

def dashboard():

    db = SessionLocal()

    while True:

        print("\n=== OMEGA BANK ===")
        print("1. View Balance")
        print("2. Exit")

        choice = input("> ")

        if choice == "1":

            wallets = db.execute(text("SELECT * FROM wallets")).fetchall()

            for w in wallets:
                print(w)

        if choice == "2":
            break


if not identity.exists():
    setup()

if login():
    dashboard()
