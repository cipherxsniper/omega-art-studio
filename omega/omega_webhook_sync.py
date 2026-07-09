#!/usr/bin/env python3
"""
OMEGA WEBHOOK SYNC v1.0
Reads the current cloudflared tunnel URL and updates the Stripe
webhook endpoint to match. Run after cloudflared (re)starts, or
periodically via guardian, to self-heal webhook delivery.
"""
import os, sys, json, re
from pathlib import Path
from dotenv import load_dotenv
import urllib.request, urllib.parse, urllib.error

HOME = Path.home()
load_dotenv(HOME / ".env")

STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY")
TUNNEL_LOG = HOME / "omega_runtime/logs/tunnel.log"
WEBHOOK_ID = "we_1TgKsNA5xsR4lvM4KIcEAdZu"  # the primary Stripe webhook endpoint
STATE_PATH = HOME / "omega_runtime/state/webhook_sync.json"

def get_current_tunnel_url():
    """Parse the most recent trycloudflare.com URL from the tunnel log."""
    if not TUNNEL_LOG.exists():
        return None
    text = TUNNEL_LOG.read_text()
    urls = re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com', text)
    return urls[-1] if urls else None

def get_webhook_url():
    req = urllib.request.Request(
        f"https://api.stripe.com/v1/webhook_endpoints/{WEBHOOK_ID}",
        headers={"Authorization": f"Bearer {STRIPE_SECRET}"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    return data.get("url")

def update_webhook_url(new_url):
    payload = urllib.parse.urlencode({"url": new_url}).encode()
    req = urllib.request.Request(
        f"https://api.stripe.com/v1/webhook_endpoints/{WEBHOOK_ID}",
        data=payload,
        headers={"Authorization": f"Bearer {STRIPE_SECRET}"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    return data

def sync():
    tunnel_url = get_current_tunnel_url()
    if not tunnel_url:
        print("No tunnel URL found in log")
        return False

    full_webhook_url = f"{tunnel_url}/webhook/stripe"
    current_stripe_url = get_webhook_url()

    print(f"Current tunnel:  {tunnel_url}")
    print(f"Current Stripe:  {current_stripe_url}")
    print(f"Target Stripe:   {full_webhook_url}")

    if current_stripe_url == full_webhook_url:
        print("✅ Already in sync — no update needed")
        return True

    result = update_webhook_url(full_webhook_url)
    print(f"✅ Updated Stripe webhook to: {result.get('url')}")

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({
        "synced_url": full_webhook_url,
        "tunnel_url": tunnel_url,
    }, indent=2))
    return True

if __name__ == "__main__":
    sync()
