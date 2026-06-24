from fastapi import FastAPI
from integrations.stripe_checkout import create_checkout_session

app = FastAPI()


@app.get("/buy/{plan}")
def buy(plan: str):
    url = create_checkout_session(
        plan=plan,
        success_url="https://yourdomain.com/success",
        cancel_url="https://yourdomain.com/cancel"
    )
    return {"checkout_url": url}
