#!/usr/bin/env python3
"""
omega_collection_pipeline.py
One command launches a new collection end-to-end:
  1. Validates collection folder structure
  2. Registers all tokens to nft_registry
  3. Creates Stripe product + price + payment link per token
  4. Writes stripe links back to nft_registry
  5. Marks founder tokens

Usage:
  python3 ~/omega_collection_pipeline.py --collection <slug> --start <id> --count 100
  python3 ~/omega_collection_pipeline.py --collection newcoll --start 3001 --count 100
"""

import os, sys, json, hashlib, time, argparse
import urllib.request, urllib.parse, psycopg2

# ── Config ───────────────────────────────────────────────────────
PG_LEDGER = "dbname=omega_ledger user=postgres host=127.0.0.1 port=5432"

def _load_env(key):
    for l in open(os.path.expanduser("~/.env")).read().splitlines():
        if l.startswith(key + "="):
            return l.split("=",1)[1].strip()
    return ""

STRIPE_SECRET = _load_env("STRIPE_SECRET_KEY")

PRICES = {
    "impossible_diamond": 250000,
    "black_diamond":       50000,
    "super_rare":          15000,
    "rare":                 7500,
    "medium":               3500,
    "common":               1500,
}

RARITY_DISPLAY = {
    "impossible_diamond": "Impossible Diamond",
    "black_diamond":      "Black Diamond",
    "super_rare":         "Super Rare",
    "rare":               "Rare",
    "medium":             "Medium",
    "common":             "Common",
}

GENESIS = {
    "echoes":   "OMEGA_GENESIS_THOMAS_LEE_HARVEY_OM109_2024",
    "somnium":  "OMEGA_GENESIS_THOMAS_LEE_HARVEY_SOMNIUM_2026",
    "paracosm": "OMEGA_GENESIS_THOMAS_LEE_HARVEY_PARACOSM_2026",
    "monolith": "OMEGA_GENESIS_THOMAS_LEE_HARVEY_OM109_2024_MONOLITH",
}

FOUNDER_COUNT = 13

# ── Stripe ───────────────────────────────────────────────────────
def stripe_post(endpoint, data):
    url = f"https://api.stripe.com/v1/{endpoint}"
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded, method="POST")
    creds = urllib.parse.b64encode(f"{STRIPE_SECRET}:".encode()).decode()
    req.add_header("Authorization", f"Basic {creds}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Stripe {e.code}: {e.read().decode()}")

# ── OM109 ────────────────────────────────────────────────────────
def om109(collection, token_id, image_hash):
    seed = GENESIS.get(collection, f"OMEGA_GENESIS_{collection.upper()}_2026")
    genesis = hashlib.sha256(seed.encode()).hexdigest()
    sig_a = hashlib.sha256(f"{genesis}:A:{token_id}:{image_hash}".encode()).hexdigest()
    sig_b = hashlib.sha256(f"{genesis}:B:{token_id}:{image_hash}:{sig_a}".encode()).hexdigest()
    fp = hashlib.sha256((sig_a[:32] + sig_b[:32]).encode()).hexdigest()
    return sig_a, sig_b, fp

def image_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

# ── Chain hash ───────────────────────────────────────────────────
def chain_hash(prev_hash, token_id, fp):
    return hashlib.sha256(f"{prev_hash}:{token_id}:{fp}".encode()).hexdigest()

# ── Rarity seed ──────────────────────────────────────────────────
RARITY_DIST = [
    ("impossible_diamond", 1),
    ("black_diamond",      4),
    ("super_rare",        10),
    ("rare",              20),
    ("medium",            30),
    ("common",            35),
]

def assign_rarity(token_id, collection):
    seed = f"{collection}:{token_id}:RARITY"
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % 100
    cumulative = 0
    for rarity, pct in RARITY_DIST:
        cumulative += pct
        if h < cumulative:
            return rarity
    return "common"

# ── Step 1: Validate folder ──────────────────────────────────────
def validate_folder(collection, start, count):
    base = os.path.expanduser(f"~/{collection}")
    images = os.path.join(base, "images")
    if not os.path.isdir(images):
        print(f"  ERROR: {images} not found")
        print(f"  Create folder and add PNG files named {{token_id}}.png")
        sys.exit(1)
    missing = []
    for i in range(start, start + count):
        p = os.path.join(images, f"{i}.png")
        if not os.path.exists(p):
            missing.append(i)
    if missing:
        print(f"  WARNING: {len(missing)} images missing: {missing[:5]}{'...' if len(missing)>5 else ''}")
        ans = input("  Continue anyway? [y/N] ").strip().lower()
        if ans != "y":
            sys.exit(0)
    print(f"  Folder OK — {count - len(missing)}/{count} images present")
    return base

# ── Step 2: Register tokens ──────────────────────────────────────
def register_tokens(collection, start, count, base):
    conn = psycopg2.connect(PG_LEDGER)
    conn.autocommit = False
    cur = conn.cursor()

    # Ensure columns exist
    cur.execute("""
        ALTER TABLE nft_registry
        ADD COLUMN IF NOT EXISTS stripe_payment_link TEXT,
        ADD COLUMN IF NOT EXISTS stripe_product_id TEXT,
        ADD COLUMN IF NOT EXISTS stripe_price_id TEXT,
        ADD COLUMN IF NOT EXISTS sold_at TIMESTAMP
    """)
    conn.commit()

    prev = hashlib.sha256(f"OMEGA_CHAIN_INIT_{collection}".encode()).hexdigest()
    registered = 0
    skipped = 0

    for i, token_id in enumerate(range(start, start + count)):
        img_path = os.path.join(base, "images", f"{token_id}.png")
        if os.path.exists(img_path):
            img_h = image_hash(img_path)
        else:
            img_h = hashlib.sha256(f"PLACEHOLDER:{token_id}".encode()).hexdigest()

        sig_a, sig_b, fp = om109(collection, token_id, img_h)
        ch = chain_hash(prev, token_id, fp)
        prev = ch

        rarity = assign_rarity(token_id, collection)
        is_founder = (i < FOUNDER_COUNT)
        sale_status = "founder" if is_founder else "unsold"
        owner = "FOUNDER_RESERVE" if is_founder else "UNASSIGNED"
        title = f"{collection.title()} #{token_id}"
        name  = f"{collection.upper()}-{token_id:04d}"

        try:
            cur.execute("""
                INSERT INTO nft_registry
                    (token_id, name, title, rarity, theme, image_sha256,
                     om109_fingerprint, om109_sig_a, om109_sig_b, chain_hash,
                     owner_account_id, is_founder_linked, sale_status, collection)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (collection, token_id) DO NOTHING
            """, (token_id, name, title, rarity, collection,
                  img_h, fp, sig_a, sig_b, ch,
                  owner, is_founder, sale_status, collection))
            registered += 1
        except Exception as e:
            conn.rollback()
            print(f"  SKIP #{token_id}: {e}")
            skipped += 1
            continue

    conn.commit()
    conn.close()
    print(f"  Registered {registered} tokens ({skipped} skipped/existing)")

# ── Step 3: Stripe products ──────────────────────────────────────
def create_stripe_products(collection, start, count):
    conn = psycopg2.connect(PG_LEDGER)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("""
        SELECT token_id, title, rarity FROM nft_registry
        WHERE collection = %s AND token_id >= %s AND token_id < %s
          AND sale_status = 'unsold'
          AND (stripe_price_id IS NULL OR stripe_price_id = '')
        ORDER BY token_id
    """, (collection, start, start + count))
    tokens = cur.fetchall()

    print(f"  Creating Stripe products for {len(tokens)} unsold tokens...")
    ok = 0
    failed = 0

    for token_id, title, rarity in tokens:
        price_cents = PRICES.get(rarity, 1500)
        rarity_label = RARITY_DISPLAY.get(rarity, rarity)
        try:
            # Product
            prod = stripe_post("products", {
                "name": f"{title} — {rarity_label}",
                "description": f"Omega Art Studio | {collection.title()} Collection | Token #{token_id} | OM109 Authenticated",
                "metadata[collection]": collection,
                "metadata[token_id]": str(token_id),
                "metadata[rarity]": rarity,
            })
            # Price
            price = stripe_post("prices", {
                "product": prod["id"],
                "unit_amount": price_cents,
                "currency": "usd",
                "metadata[collection]": collection,
                "metadata[token_id]": str(token_id),
            })
            # Payment link
            link = stripe_post("payment_links", {
                "line_items[0][price]": price["id"],
                "line_items[0][quantity]": "1",
                "metadata[collection]": collection,
                "metadata[token_id]": str(token_id),
            })

            cur.execute("""
                UPDATE nft_registry
                SET stripe_product_id = %s,
                    stripe_price_id = %s,
                    stripe_payment_link = %s
                WHERE collection = %s AND token_id = %s
            """, (prod["id"], price["id"], link["url"], collection, token_id))
            conn.commit()
            ok += 1
            if ok % 10 == 0:
                print(f"    {ok}/{len(tokens)} done...")
            time.sleep(0.15)  # rate limit safety

        except Exception as e:
            conn.rollback()
            print(f"  FAIL #{token_id}: {e}")
            failed += 1

    conn.close()
    print(f"  Stripe done — {ok} created, {failed} failed")

# ── Main ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Omega Collection Pipeline")
    parser.add_argument("--collection", required=True, help="Collection slug (e.g. echoes, newcoll)")
    parser.add_argument("--start",      required=True, type=int, help="First token ID")
    parser.add_argument("--count",      default=100,   type=int, help="Number of tokens (default 100)")
    parser.add_argument("--skip-stripe", action="store_true", help="Skip Stripe (register only)")
    args = parser.parse_args()

    coll  = args.collection.lower()
    start = args.start
    count = args.count

    print(f"\n OMEGA COLLECTION PIPELINE")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Collection : {coll}")
    print(f"  Token IDs  : {start} — {start + count - 1}")
    print(f"  Count      : {count}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    print(f"\n[1/3] Validating folder structure...")
    base = validate_folder(coll, start, count)

    print(f"\n[2/3] Registering tokens to nft_registry...")
    register_tokens(coll, start, count, base)

    if not args.skip_stripe:
        print(f"\n[3/3] Creating Stripe products + payment links...")
        create_stripe_products(coll, start, count)
    else:
        print(f"\n[3/3] Skipping Stripe (--skip-stripe flag set)")

    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  PIPELINE COMPLETE")
    print(f"  Gallery auto-includes via /collection/{coll}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

if __name__ == "__main__":
    main()
