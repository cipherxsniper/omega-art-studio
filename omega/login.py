import json
import os

FILE = "omega_user.json"

def setup_user():
    if os.path.exists(FILE):
        return json.load(open(FILE))

    pin = input("Create 4-digit PIN: ")
    pin2 = input("Confirm PIN: ")

    if pin != pin2:
        print("PIN mismatch")
        exit()

    name = input("Enter your Omega name: ")

    user = {
        "pin": pin,
        "name": name,
        "uuid": __import__("uuid").uuid4().hex
    }

    json.dump(user, open(FILE, "w"))
    return user
