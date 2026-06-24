import urllib.request, json, os, re, time, urllib.parse
from dotenv import load_dotenv
load_dotenv()

STRIPE_KEY = os.getenv('STRIPE_SECRET_KEY')
LOG = os.path.expanduser('~/omega_runtime/logs/cloudflared.log')

def get_current_tunnel_url():
    try:
        with open(LOG) as f:
            content = f.read()
        urls = re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com', content)
        return urls[-1] if urls else None
    except:
        return None

def get_current_webhook():
    try:
        req = urllib.request.Request(
            'https://api.stripe.com/v1/webhook_endpoints',
            headers={'Authorization': f'Bearer {STRIPE_KEY}'}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        if data['data']:
            return data['data'][0]['id'], data['data'][0]['url']
        return None, None
    except Exception as e:
        print(f'Error checking webhook: {e}')
        return None, None

def update_stripe_webhook(endpoint_id, url):
    full_url = f'{url}/webhook/stripe'
    data = urllib.parse.urlencode({'url': full_url}).encode()
    req = urllib.request.Request(
        f'https://api.stripe.com/v1/webhook_endpoints/{endpoint_id}',
        data=data, method='POST',
        headers={'Authorization': f'Bearer {STRIPE_KEY}'}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

print('Tunnel sync watchdog started')
last_url = None

while True:
    try:
        current = get_current_tunnel_url()
        if current and current != last_url:
            ep_id, current_webhook_url = get_current_webhook()
            if ep_id and current not in (current_webhook_url or ''):
                print(f'Tunnel changed to {current} — updating Stripe')
                result = update_stripe_webhook(ep_id, current)
                print(f'Stripe webhook updated: {result.get("url")}')
            last_url = current
    except Exception as e:
        print(f'Sync error: {e}')
    time.sleep(30)
