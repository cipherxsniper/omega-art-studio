import urllib.request as ur
import json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv('STRIPE_SECRET_KEY')
req = ur.Request(
    'https://api.stripe.com/v1/payment_intents?limit=5',
    headers={'Authorization': f'Bearer {key}'}
)
with ur.urlopen(req, timeout=10) as r:
    data = json.loads(r.read())

for pi in data.get('data', []):
    print(f"Amount: ${pi['amount']/100:.2f} | Status: {pi['status']} | Created: {pi['created']}")
