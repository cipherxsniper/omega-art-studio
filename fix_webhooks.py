import urllib.request, json, urllib.parse, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv('STRIPE_SECRET_KEY')

def stripe_get(path):
    req = urllib.request.Request(
        f'https://api.stripe.com/v1{path}',
        headers={'Authorization': f'Bearer {key}'}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def stripe_delete(endpoint_id):
    req = urllib.request.Request(
        f'https://api.stripe.com/v1/webhook_endpoints/{endpoint_id}',
        method='DELETE',
        headers={'Authorization': f'Bearer {key}'}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def stripe_create(url, events):
    data = urllib.parse.urlencode([
        ('url', url),
        *[('enabled_events[]', e) for e in events]
    ]).encode()
    req = urllib.request.Request(
        'https://api.stripe.com/v1/webhook_endpoints',
        data=data, method='POST',
        headers={'Authorization': f'Bearer {key}'}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

endpoints = stripe_get('/webhook_endpoints')['data']
print(f'Found {len(endpoints)} endpoints — deleting all...')
for ep in endpoints:
    stripe_delete(ep['id'])
    print(f"Deleted: {ep['url']}")

current_url = "https://newton-thomson-computer-weblog.trycloudflare.com/webhook/stripe"
new_ep = stripe_create(current_url, [
    'checkout.session.completed',
    'customer.subscription.created',
    'customer.subscription.deleted',
    'invoice.paid',
    'invoice.payment_failed',
    'payment_intent.succeeded'
])
print(f"\nCreated single clean endpoint:")
print(f"URL: {new_ep['url']}")
print(f"Secret: {new_ep['secret']}")
