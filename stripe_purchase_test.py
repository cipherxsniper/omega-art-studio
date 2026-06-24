import sys, json
from omega_card_engine import issue_card, authorize_transaction

def run_test():
    print("=== OMEGA STRIPE PURCHASE TEST ===")
    card = issue_card("7597e069-65bc-4b55-b420-a2a2682f53e0", "Thomas Lee Harvey")
    token = card.get("card_token")
    pan = card.get("pan")
    cvv = card.get("cvv")
    print("Card Issued: " + str(token))
    print("PAN: " + str(pan) + " | CVV: " + str(cvv))
    price_id = "price_TXZ9DA5xsR4lvM47e8aC560"
    print("Attempting purchase for: " + str(price_id))
    result = authorize_transaction(token, 99.00, "STRIPE_" + str(price_id), cvv)
    print("
Result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    run_test()
