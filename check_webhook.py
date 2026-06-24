import urllib.request, json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv('STRIPE_SECRET_KEY')
req = urllib.request.Request(
    'https://api.stripe.com/v1/webhook_endpoints',
    headers={'Authorization': f'Bearer {key}'}
)
with urllib.request.urlopen(req, timeout=10) as r:
    data = json.loads(r.read())

for ep in data.get('data', []):
    print(f"URL: {ep['url']}")
    print(f"Status: {ep['status']}")
    print(f"Events: {ep['enabled_events'][:3]}...")
    print('---')
