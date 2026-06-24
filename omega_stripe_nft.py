#!/usr/bin/env python3
"""
Omega NFT Stripe Product Creator
- Reads 348 UNASSIGNED tokens from omega_ledger.nft_registry
- Creates Stripe product + price + payment link per token
- Writes stripe_payment_link back to nft_registry
- urllib only, no SDK
"""
import json, time, urllib.request, urllib.parse, psycopg2
from datetime import datetime

STRIPE_SECRET = open("/data/data/com.termux/files/home/.env").read()
STRIPE_SECRET = [l.split("=",1)[1].strip() for l in STRIPE_SECRET.splitlines() if l.startswith("STRIPE_SECRET_KEY=")][0]

PG_LEDGER = "dbname=omega_ledger user=postgres host=127.0.0.1 port=5432"

PRICES = {
    "Impossible Diamond": 250000,  # $2,500.00 in cents
    "Black Diamond":       50000,  # $500.00
    "Super Rare":          15000,  # $150.00
    "Rare":                 7500,  # $75.00
    "Medium":               3500,  # $35.00
    "Common":               1500,  # $15.00
}

def stripe_post(endpoint, data):
    """POST to Stripe API using urllib only."""
    url = f"https://api.stripe.com/v1/{endpoint}"
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded, method="POST")
    req.add_header("Authorization", f"Bearer {STRIPE_SECRET}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"Stripe error {e.code}: {body}")

def add_payment_link_column():
    conn = psycopg2.connect(PG_LEDGER)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        ALTER TABLE nft_registry
        ADD COLUMN IF NOT EXISTS stripe_payment_link TEXT,
        ADD COLUMN IF NOT EXISTS stripe_product_id TEXT,
        ADD COLUMN IF NOT EXISTS stripe_price_id TEXT
    """)
    cur.close()
    conn.close()
    print("  Columns ready")

def get_unassigned_tokens():
    conn = psycopg2.connect(PG_LEDGER)
    cur = conn.cursor()
    cur.execute("""
        SELECT token_id, collection, title, rarity, theme
        FROM nft_registry
        WHERE owner_account_id = 'UNASSIGNED'
          AND (stripe_payment_link IS NULL OR stripe_payment_link = '')
        ORDER BY collection, token_id
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def write_stripe_data(token_id, collection, product_id, price_id, payment_link):
    conn = psycopg2.connect(PG_LEDGER)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        UPDATE nft_registry
        SET stripe_product_id = %s,
            stripe_price_id = %s,
            stripe_payment_link = %s,
            sale_status = 'for_sale'
        WHERE token_id = %s AND collection = %s
    """, (product_id, price_id, payment_link, token_id, collection))
    cur.close()
    conn.close()

def process_token(token_id, collection, title, rarity, theme):
    price_cents = PRICES.get(rarity, 1500)
    collection_slug = collection.replace(" ", "_").lower()
    token_str = str(token_id).zfill(4)

    # Create Stripe product
    product = stripe_post("products", {
        "name": f"{collection} #{token_str} — {title}",
        "description": f"{rarity} | {theme or collection} | Omega Art Studio | OM109 authenticated | Token #{token_str}",
        "metadata[collection]": collection,
        "metadata[token_id]": str(token_id),
        "metadata[rarity]": rarity,
        "metadata[collection_slug]": collection_slug,
    })
    product_id = product["id"]

    # Create price
    price = stripe_post("prices", {
        "product": product_id,
        "unit_amount": price_cents,
        "currency": "usd",
        "metadata[token_id]": str(token_id),
        "metadata[collection]": collection,
    })
    price_id = price["id"]

    # Create payment link
    link = stripe_post("payment_links", {
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "metadata[token_id]": str(token_id),
        "metadata[collection]": collection,
        "metadata[rarity]": rarity,
    })
    payment_url = link["url"]

    write_stripe_data(token_id, collection, product_id, price_id, payment_url)
    return payment_url

def main():
    print("\n" + "="*60)
    print("  OMEGA NFT — STRIPE PRODUCT CREATOR")
    print("="*60)

    print("\n[1/4] Adding columns to nft_registry...")
    add_payment_link_column()

    print("[2/4] Loading unassigned tokens...")
    tokens = get_unassigned_tokens()
    print(f"  Found {len(tokens)} tokens to process")

    if not tokens:
        print("  Nothing to do — all tokens already have payment links")
        return

    print(f"\n[3/4] Creating Stripe products ({len(tokens)} tokens)...")
    success = 0
    failed = 0
    failed_list = []

    for i, (token_id, collection, title, rarity, theme) in enumerate(tokens, 1):
        try:
            url = process_token(token_id, collection, title, rarity, theme)
            price_display = PRICES.get(rarity, 1500) / 100
            print(f"  [{i:3d}/{len(tokens)}] {collection} #{str(token_id).zfill(4)} {rarity} ${price_display:.2f} → {url}")
            success += 1
            # Rate limit: Stripe allows 100 req/s, we do 3 calls per token
            # Stay well under with a small sleep
            time.sleep(0.3)
        except Exception as e:
            print(f"  [{i:3d}/{len(tokens)}] ERROR {collection} #{token_id}: {e}")
            failed += 1
            failed_list.append((token_id, collection, str(e)))
            time.sleep(1)

    print(f"\n[4/4] Complete")
    print(f"  ✅ Success: {success}")
    print(f"  ❌ Failed:  {failed}")

    if failed_list:
        print("\n  Failed tokens:")
        for tid, col, err in failed_list:
            print(f"    {col} #{tid}: {err}")

    print("="*60 + "\n")

if __name__ == "__main__":
    main()
