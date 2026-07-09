INSTITUTIONAL_ACCOUNTS = {
    "OMEGA_TREASURY": {
        "name": "OMEGA_TREASURY",
        "type": "TREASURY",
        "address": "acd27fe4-1862-48ff-a343-5595cc7ca49b",
        "frozen": True
    },

    "THOMAS_LEE_HARVEY": {
        "name": "THOMAS_LEE_HARVEY",
        "type": "FOUNDER",
        "address": "7fb91891-2f60-4edb-8600-e9c42c4ac33c",
        "frozen": True
    },

    "OMEGA_CREDIT": {
        "name": "OMEGA_CREDIT",
        "type": "CREDIT",
        "address": "a74c8ad9-06c3-42ba-b4c2-a3b62a493106",
        "frozen": True
    },

    "OMEGA_INVESTMENT": {
        "name": "OMEGA_INVESTMENT",
        "type": "INVESTMENT",
        "address": "823a17d1-2846-4006-a631-ba48f9a88de4",
        "frozen": True
    },

    "OMEGA_SYSTEM_RESERVE": {
        "name": "OMEGA_SYSTEM_RESERVE",
        "type": "SYSTEM",
        "address": "99238820-7da1-4afd-93f5-c37fa6ad669b",
        "frozen": True
    }
}


if __name__ == "__main__":

    print("🏦 OMEGA INSTITUTIONAL ACCOUNTS v1")
    print("🔒 CANONICAL IDENTITIES FROZEN\n")

    for key, acct in INSTITUTIONAL_ACCOUNTS.items():

        print(key)
        print(f"NAME:    {acct['name']}")
        print(f"TYPE:    {acct['type']}")
        print(f"ADDRESS: {acct['address']}")
        print(f"FROZEN:  {acct['frozen']}")
        print("-" * 60)
