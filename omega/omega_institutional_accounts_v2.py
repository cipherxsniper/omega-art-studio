from decimal import Decimal

INSTITUTIONAL_ACCOUNTS = {

    "TREASURY": {
        "name": "OMEGA_TREASURY",
        "account_type": "TREASURY",
        "account_id": "acd27fe4-1862-48ff-a343-5595cc7ca49b",
        "frozen": True,
        "target_balance": Decimal("12500000000.00")
    },

    "FOUNDER": {
        "name": "THOMAS_LEE_HARVEY",
        "account_type": "FOUNDER",
        "account_id": "7fb91891-2f60-4edb-8600-e9c42c4ac33c",
        "frozen": True,
        "target_balance": Decimal("50000000.00")
    },

    "CREDIT": {
        "name": "OMEGA_CREDIT",
        "account_type": "CREDIT",
        "account_id": "a74c8ad9-06c3-42ba-b4c2-a3b62a493106",
        "frozen": True,
        "target_balance": Decimal("250000000.00")
    },

    "INVESTMENT": {
        "name": "OMEGA_INVESTMENT",
        "account_type": "INVESTMENT",
        "account_id": "823a17d1-2846-4006-a631-ba48f9a88de4",
        "frozen": True,
        "target_balance": Decimal("500000000.00")
    },

    "RESERVE": {
        "name": "OMEGA_SYSTEM_RESERVE",
        "account_type": "SYSTEM",
        "account_id": "99238820-7da1-4afd-93f5-c37fa6ad669b",
        "frozen": True,
        "target_balance": Decimal("-13300000000.00")
    }
}


if __name__ == "__main__":

    print("🏦 OMEGA INSTITUTIONAL ACCOUNTS v2")
    print("🔒 SEMANTIC REGISTRY FROZEN\n")

    for key, acct in INSTITUTIONAL_ACCOUNTS.items():

        print(key)
        print(f"NAME:           {acct['name']}")
        print(f"TYPE:           {acct['account_type']}")
        print(f"ACCOUNT_ID:     {acct['account_id']}")
        print(f"TARGET_BALANCE: {acct['target_balance']}")
        print(f"FROZEN:         {acct['frozen']}")
        print("-" * 60)

