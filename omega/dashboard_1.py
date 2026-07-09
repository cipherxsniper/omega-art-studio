import json

def load():
    return json.load(open("omega_user.json"))

def show():
    u = load()

    print("\nOMEGA BANK DASHBOARD")
    print("====================")
    print("User:", u["name"])
    print("UUID:", u["uuid"])
    print("====================\n")
