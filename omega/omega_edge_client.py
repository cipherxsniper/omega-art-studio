import requests
import uuid
import json

OMEGA_SERVER = "http://192.168.11.163:8080/event"

payload = {
    "event_id": str(uuid.uuid4()),
    "type": "OMEGA_PAY_AUTH",
    "wallet_id": "70e8cdae-983c-4392-a97a-4ae06217b303",
    "amount": 10.00,
    "merchant": "OMEGA_STORE",
    "currency": "USD"
}

r = requests.post(OMEGA_SERVER, json=payload)

print(json.dumps(r.json(), indent=2))
