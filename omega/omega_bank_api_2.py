from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def health():
    return {"status": "omega_api_alive"}
from fastapi import FastAPI
from patch_add_webhook_to_api import attach_webhook

app = FastAPI()

attach_webhook(app)
