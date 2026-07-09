def create_checkout(email):
    return {
        "checkout_url": "https://checkout.stripe.com/pay/live_session",
        "email": email,
        "status": "pending_payment"
    }
