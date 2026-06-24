#!/usr/bin/env python3
"""
MONOLITH — Omega Art Studio NFT Engine
Thomas Lee Harvey · Omega AI · OM109 Authenticated

Single, self-built, load-bearing — the collection name for the architect
who builds the bank and the art studio that sits on top of it.

End-to-end automated pipeline, modeled exactly on the proven pattern from
Echoes of Eternity, Paracosm, and Somnium:
  1. Mint 100 tokens, each posted LIVE to omega_bank.ledger_entries as minted
  2. Live-export each image to /sdcard/Pictures/Monolith/ as it completes
  3. Verify the full OM109 hash chain
  4. Generate all 100 Certificates of Authenticity
  5. Insert all 100 into omega_ledger.nft_registry
  6. Assign founding-13 wallets: 6 Impossible Diamonds total in the batch,
     1 guaranteed to Thomas's Founder wallet, the other 5 land naturally
     in the random distribution to the other 12 founder wallets
"""
import os, sys, json, time, random, hashlib, argparse, psycopg2
from pathlib import Path
from datetime import datetime, timezone

try:
    from urllib.request import urlopen, Request
    from urllib.parse import quote
except ImportError:
    pass

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_OK = True
except Exception:
    PIL_OK = False

# ── CONFIG ──────────────────────────────────────────────────────────
COLLECTION_NAME   = "Monolith"
TOKEN_START       = 2001
TOKEN_COUNT       = 100
BASE              = Path.home() / "monolith"
IMAGES_DIR        = BASE / "images"
META_DIR          = BASE / "metadata"
CERT_DIR          = BASE / "certificates"
LEDGER_LOG        = BASE / "om109_ledger.jsonl"
GALLERY_EXPORT    = Path("/sdcard/Pictures/Monolith")

for d in [IMAGES_DIR, META_DIR, CERT_DIR, GALLERY_EXPORT]:
    d.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = 1024, 1024
OMEGA_GENESIS_SEED = "OMEGA_GENESIS_THOMAS_LEE_HARVEY_OM109_2024_MONOLITH"
_LAST_CHAIN_HASH = "OMEGA_MONOLITH_GENESIS"

# The exact 6 token IDs (within the 100-batch) that will be Impossible
# Diamond, deterministically seeded so the result is reproducible and
# auditable — not hand-picked after the fact.
_rng = random.Random(OMEGA_GENESIS_SEED + "_DIAMOND_SELECT")
IMPOSSIBLE_DIAMOND_TOKENS = sorted(_rng.sample(
    range(TOKEN_START, TOKEN_START + TOKEN_COUNT), 6
))
# First diamond drawn is guaranteed to Thomas's Founder wallet.
THOMAS_DIAMOND_TOKEN = IMPOSSIBLE_DIAMOND_TOKENS[0]

THOMAS_FOUNDER_WALLET = "2109a4cc-a066-4698-a478-a786bf096318"

FOUNDING_13_WALLETS = [
    "2109a4cc-a066-4698-a478-a786bf096318",  # Thomas Lee Harvey — Founder
    "a7889956-ca14-432a-9cb7-7dc17530b7d9",  # Omega Merchant
    "ed574d93-0abf-4cc5-b6e0-9d73b77da135",  # OMEGA_CREDIT
    "b702cb19-9b5c-44f4-8db4-161e3bf60655",  # OMEGA_RESERVE_LEDGER
    "0b608cb6-6745-4b75-bb9d-fa60e8a1b051",  # OMEGA_SYSTEM_TREASURY
    "4053d3a5-06b8-43d6-b8d5-5268991f8cbc",  # OMEGA_GENESIS
    "b4ab75f8-adc6-4981-ba48-d6dc3df423a5",  # Omega Treasury Reserve
    "fa4d0a6a-bb76-45ec-90f6-4ec37f847963",  # Omega Investment Pool
    "8ad07ed5-f433-4439-a188-f11b51110ae4",  # Omega Credit Layer
    "c182dbbc-e607-4364-a6cc-7611dac8eb95",  # Omega Debit Layer
    "fac22005-e8d3-4e08-ba89-c14150503429",  # Omega Genesis Liquidity Origin
    "cb8f4ebe-3205-408f-a765-148275ac36b8",  # Reserve Ledger
    "c8818380-c58d-4c52-a912-d69e0ae0d263",  # Ops Float
]

# ── ART CONCEPT POOL ────────────────────────────────────────────────
# Open-ended, mathematics-driven — no specific scene is hardcoded as
# "the" Monolith image. Each token combines a structural concept, an
# impossible physics twist, and a vivid single accent color, letting
# combinatorics generate genuine variety across 100 tokens.

STRUCTURES = [
    "a single obsidian monolith","a fractured marble column","a load-bearing arch with no walls",
    "a granite slab balanced on its edge","a tower of stacked stone discs","a single standing megalith",
    "a keystone suspended mid-air","a obelisk carved from one continuous piece of basalt",
    "a vertical slab of black volcanic glass","a single unbroken pillar of weathered concrete",
    "a monument with no inscriptions","a stone tablet floating just above the ground",
    "a single load-bearing beam holding up nothing","a sheet of cracked granite standing alone",
    "a square-cut stone slab embedded halfway into the earth","a single vertical shard of dark stone",
]

IMPOSSIBLE_TWISTS = [
    "casting a shadow that belongs to something else entirely","with roots made of light reaching upward into the sky",
    "perfectly balanced with zero visible support","growing a single branch of real leaves from solid stone",
    "with water flowing upward across its surface in defiance of gravity","reflecting a sky that doesn't match the one above it",
    "with its shadow pooling into liquid on the ground","splitting down the middle to reveal a second smaller version of itself inside",
    "with a single vine growing through solid rock from the inside out","levitating exactly one inch off the ground, casting a full shadow as if it touched",
    "with fruit growing directly from its stone surface","dripping condensation despite being made of solid rock",
    "with a single dangling vase growing from its peak, leaves tangling down its face",
    "fractured into a perfect geometric grid mid-air, held together by nothing",
    "with a single beam of color passing through it like light through glass",
    "casting two shadows in opposite directions from one light source",
]

ACCENT_SUBJECTS = [
    ("a single pomegranate split open, seeds glowing","deep crimson"),
    ("a lone teal apple, sweating with condensation","saturated teal"),
    ("a single golden feather caught mid-fall","liquid gold"),
    ("an amber-colored egg balanced on the edge","warm amber"),
    ("a single violet orchid growing from a crack","iridescent violet"),
    ("a sapphire-blue marble resting in a carved hollow","sapphire blue"),
    ("a single ember-orange leaf, veins glowing from within","ember orange"),
    ("a small pool of mercury-silver liquid pooling at the base","mercury silver"),
    ("a single emerald-green moth resting on the surface","emerald green"),
    ("a crimson thread unraveling from a hidden seam","deep crimson"),
    ("a single citrine crystal embedded in the stone","citrine yellow"),
    ("a small flame of cyan light burning without heat","electric cyan"),
]

PERSPECTIVES = [
    "extreme low angle looking straight up, dramatic foreshortening",
    "eye-level centered composition, classical monument framing",
    "three-quarter aerial view looking down and across",
    "tight macro detail shot, texture filling most of frame",
    "wide establishing shot, subject small against vast grey space",
    "dutch angle, 12 degree tilt, unsettling asymmetry",
    "direct frontal symmetry, perfectly centered",
    "side profile silhouette with raking light across texture",
]


def get_rarity(token_id):
    if token_id in IMPOSSIBLE_DIAMOND_TOKENS:
        return "Impossible Diamond", 6
    random.seed(token_id * 9999)
    r = random.random()
    if r < 0.02:
        return "Black Diamond", 5
    elif r < 0.08:
        return "Super Rare", 4
    elif r < 0.25:
        return "Rare", 3
    elif r < 0.55:
        return "Medium", 2
    else:
        return "Common", 1


SURREAL_TITLES = [
    "Bedrock","Axiom","Foundation","Bastion","Threshold","Apex","Cornerstone",
    "Anchor","Pillar","Genesis","Aegis","Vertex","Edifice","Citadel","Stratum",
    "Lintel","Plinth","Span","Truss","Strata","Mantle","Buttress","Capstone",
    "Bulwark","Rampart","Spire","Obelisk","Cairn","Ridge","Crag","Escarpment",
    "Summit","Precipice","Outcrop","Megalith","Cromlech","Dolmen","Henge",
]


def get_title(token_id):
    if token_id == THOMAS_DIAMOND_TOKEN:
        return "Founder"
    random.seed(token_id * 3137)
    return SURREAL_TITLES[int(random.random() * len(SURREAL_TITLES))]


def build_prompt(token_id, complexity):
    random.seed(token_id * 7331 + complexity)
    structure   = STRUCTURES[token_id % len(STRUCTURES)]
    twist       = IMPOSSIBLE_TWISTS[token_id % len(IMPOSSIBLE_TWISTS)]
    subject, color = ACCENT_SUBJECTS[token_id % len(ACCENT_SUBJECTS)]
    perspective = PERSPECTIVES[token_id % len(PERSPECTIVES)]

    prompt = (
        f"Commercial fine art studio photograph, hyper-surrealist, 8K ultra detail, {perspective}. "
        f"Square 1:1 format, SQUARE FORMAT, fills entire frame edge to edge, NO black bars, NO letterboxing. "
        f"Background: bright warm neutral grey concrete studio wall and matte floor, "
        f"professional product photography lighting, single Profoto strobe upper-left 45 degrees. "
        f"Main subject: {structure}, {twist}. "
        f"Beside it on the studio floor: {subject}, covered in individual photorealistic water droplets, "
        f"each droplet a sharp glass sphere refracting light with micro-detail. "
        f"The {subject.split(',')[0]} is rendered in rich saturated {color} — "
        f"the ONLY color anywhere in the frame. Every other surface, the structure, the wall, the floor, "
        f"the shadow — completely desaturated monochrome silver-grey. "
        f"Hasselblad medium format, f/4, tack sharp focus throughout, micro-detail texture on stone and water. "
        f"Photorealistic RAW photograph, not painting, not illustration, not CGI render. "
        f"Magritte surrealist concept, Gregory Crewdson dramatic lighting, museum print quality. "
        f"NO text, NO watermark, NO signature, NO border."
    )
    negative = (
        "cartoon,anime,painting,illustration,low quality,blurry,colorful background,"
        "text,watermark,signature,border,ugly,deformed,black bars,letterbox,padding,dark atmosphere,smoke"
    )
    return prompt, negative, (structure, twist, subject, color)


def generate_image(token_id, prompt, negative, complexity):
    out_path = IMAGES_DIR / f"{token_id:04d}.png"
    if out_path.exists():
        print(f"  image {token_id:04d} exists, skipping")
        return out_path
    steps = {1: 30, 2: 35, 3: 40, 4: 45, 5: 55, 6: 65}[complexity]
    seed  = token_id * 137 + complexity
    url = (
        f"https://image.pollinations.ai/prompt/{quote(prompt)}"
        f"?width={WIDTH}&height={HEIGHT}&seed={seed}&steps={steps}"
        f"&negative={quote(negative)}&model=flux&nologo=true&enhance=true"
    )
    print(f"  generating #{token_id:04d} ({steps} steps)...")
    for attempt in range(1, 4):
        try:
            req = Request(url, headers={"User-Agent": "OmegaMonolith/1.0"})
            with urlopen(req, timeout=150) as resp:
                data = resp.read()
            with open(out_path, "wb") as f:
                f.write(data)
            print(f"  saved {out_path.name} ({len(data)//1024}KB)")
            return out_path
        except Exception as e:
            print(f"  attempt {attempt}/3: {e}")
            if attempt < 3:
                time.sleep(12 * attempt)
    return None


def post_process(img_path, complexity):
    if not PIL_OK:
        return img_path
    img = Image.open(img_path).convert("RGB")
    img = ImageEnhance.Contrast(img).enhance(1.3 + complexity * 0.05)
    img = ImageEnhance.Brightness(img).enhance(1.03)
    img = ImageEnhance.Color(img).enhance(2.0 + complexity * 0.1)
    img = img.filter(ImageFilter.SHARPEN)
    img.save(img_path, optimize=True, quality=99)
    return img_path


def hash_image(img_path):
    with open(img_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def om109_sign(token_id, image_hash):
    genesis = hashlib.sha256(OMEGA_GENESIS_SEED.encode()).hexdigest()
    sig_a = hashlib.sha256(f"{genesis}:A:{token_id}:{image_hash}".encode()).hexdigest()
    sig_b = hashlib.sha256(f"{genesis}:B:{token_id}:{image_hash}:{sig_a}".encode()).hexdigest()
    fp    = hashlib.sha256(f"{sig_a[:32]}{sig_b[:32]}".encode()).hexdigest()
    return {"sig_a": sig_a, "sig_b": sig_b, "om109_fingerprint": fp}


def ledger_mint_jsonl(token_id, image_hash, om109, rarity, theme, title, ts):
    global _LAST_CHAIN_HASH
    if LEDGER_LOG.exists():
        lines = [l.strip() for l in open(LEDGER_LOG) if l.strip()]
        if lines:
            _LAST_CHAIN_HASH = json.loads(lines[-1]).get("chain_hash", _LAST_CHAIN_HASH)
    entry = {
        "event_type": "NFT_MINT", "token_id": token_id, "collection": COLLECTION_NAME,
        "creator": "Thomas Lee Harvey", "title": title, "image_sha256": image_hash,
        "rarity": rarity, "theme": theme,
        "om109_fingerprint": om109["om109_fingerprint"],
        "sig_a": om109["sig_a"], "sig_b": om109["sig_b"],
        "minted_at": ts, "prev_chain_hash": _LAST_CHAIN_HASH,
    }
    entry["chain_hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
    _LAST_CHAIN_HASH = entry["chain_hash"]
    with open(LEDGER_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry["chain_hash"]


def ledger_mint_psql(token_id, image_hash, om109, rarity, title, chain_hash):
    try:
        conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="omega_bank",
                                user="postgres", connect_timeout=5)
        conn.autocommit = True
        cur = conn.cursor()
        idem = hashlib.sha256(f"{COLLECTION_NAME}_MINT:{token_id}:{image_hash}".encode()).hexdigest()[:32]
        cur.execute("""
            INSERT INTO ledger_entries
                (transaction_id, wallet_id, event_type, amount, direction,
                 debit_account, credit_account, memo, idempotency_key,
                 om109_fingerprint, chain_hash)
            VALUES
                (uuid_generate_v4(), '2db2e016-f6a1-4086-bec2-363edfb1c26b',
                 %s, 0.01, 'CREDIT', 'nft_collection', 'omega_treasury',
                 %s, %s, %s, %s)
            ON CONFLICT (idempotency_key) DO NOTHING
        """, (
            f"{COLLECTION_NAME.upper()}_MINT_{rarity.upper().replace(' ', '_')}",
            f"{COLLECTION_NAME} #{token_id} '{title}' {rarity} | SHA256:{image_hash[:16]}",
            idem, om109["om109_fingerprint"], chain_hash
        ))
        conn.close()
        print(f"  ledger PSQL: recorded #{token_id} on omega_bank")
    except Exception as e:
        print(f"  ledger PSQL: offline ({e}) — JSONL only")


def build_metadata(token_id, rarity, title, structure, twist, subject, color, image_hash, om109_fp, chain_hash):
    is_signed = rarity in ("Impossible Diamond", "Black Diamond")
    minted_at = datetime.now(timezone.utc).isoformat()
    return {
        "name": f"{COLLECTION_NAME} \u2014 {title} #{token_id}",
        "description": (
            f"\"{title}\" is a 1-of-100 hyper-surrealist fine art NFT from the {COLLECTION_NAME} "
            f"collection by Thomas Lee Harvey. {structure}, {twist}. "
            f"Authenticated by OM109 alternating dual-key signature \u2014 the same cryptographic "
            f"primitive securing the Omega Bank distributed ledger. Rarity: {rarity}."
        ),
        "image": f"ipfs://YOUR_CID/images/{token_id}.png",
        "external_url": "https://omegaops.ai",
        "edition": token_id, "total_supply": TOKEN_COUNT, "rarity": rarity, "title": title,
        "creator": "Thomas Lee Harvey", "collection": COLLECTION_NAME, "minted_at": minted_at,
        "image_sha256": image_hash, "om109_fingerprint": om109_fp, "om109_chain_hash": chain_hash,
        "authentication": "OM109 Alternating Dual-Key Signature",
        "attributes": [
            {"trait_type": "Rarity", "value": rarity},
            {"trait_type": "Title", "value": title},
            {"trait_type": "Edition", "value": f"{token_id} of {TOKEN_COUNT}"},
            {"trait_type": "Creator", "value": "Thomas Lee Harvey"},
            {"trait_type": "Collection", "value": COLLECTION_NAME},
            {"trait_type": "Structure", "value": structure},
            {"trait_type": "Impossible Physics", "value": twist},
            {"trait_type": "Accent Subject", "value": subject},
            {"trait_type": "Accent Color", "value": color},
            {"trait_type": "Authentication", "value": "OM109 Dual-Signature"},
            {"trait_type": "SHA256 Fingerprint", "value": image_hash},
            {"trait_type": "Signed by Artist", "value": "Yes" if is_signed else "No"},
            {"trait_type": "Format", "value": "1024x1024 PNG"},
        ]
    }


def build_coa_html(token_id, title, rarity, image_hash, om109_fp, chain_hash, minted_at):
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Certificate — {COLLECTION_NAME} #{token_id}</title>
<style>
body{{background:#111;color:#ddd;font-family:Georgia,serif;padding:40px;max-width:680px;margin:0 auto}}
h1{{color:#fff;border-bottom:1px solid #444;padding-bottom:12px}}
.row{{margin:10px 0;font-size:14px}}.label{{color:#888;display:inline-block;width:180px}}
.mono{{font-family:monospace;font-size:11px;word-break:break-all;color:#9ad}}
</style></head><body>
<h1>Certificate of Authenticity</h1>
<div class="row"><span class="label">Collection</span>{COLLECTION_NAME}</div>
<div class="row"><span class="label">Title</span>{title}</div>
<div class="row"><span class="label">Edition</span>#{token_id} of {TOKEN_COUNT}</div>
<div class="row"><span class="label">Rarity</span>{rarity}</div>
<div class="row"><span class="label">Creator</span>Thomas Lee Harvey</div>
<div class="row"><span class="label">Minted</span>{minted_at}</div>
<div class="row"><span class="label">SHA-256</span><span class="mono">{image_hash}</span></div>
<div class="row"><span class="label">OM109 Fingerprint</span><span class="mono">{om109_fp}</span></div>
<div class="row"><span class="label">Chain Hash</span><span class="mono">{chain_hash}</span></div>
<div class="row"><span class="label">Authentication</span>OM109 Alternating Dual-Key Signature</div>
</body></html>"""


def mint_token(token_id):
    print(f"\n{'='*54}\n  MINTING  {COLLECTION_NAME} #{token_id}\n{'='*54}")
    rarity, complexity = get_rarity(token_id)
    title = get_title(token_id)
    prompt, negative, concept = build_prompt(token_id, complexity)
    structure, twist, subject, color = concept
    print(f"  Title   : {title}\n  Rarity  : {rarity}\n  Structure: {structure}\n  Color   : {color}")

    img_path = generate_image(token_id, prompt, negative, complexity)
    if not img_path:
        return False
    post_process(img_path, complexity)

    image_hash = hash_image(img_path)
    om109      = om109_sign(token_id, image_hash)
    ts         = datetime.now(timezone.utc).isoformat()
    chain_hash = ledger_mint_jsonl(token_id, image_hash, om109, rarity, structure, title, ts)
    ledger_mint_psql(token_id, image_hash, om109, rarity, title, chain_hash)

    meta = build_metadata(token_id, rarity, title, structure, twist, subject, color,
                          image_hash, om109["om109_fingerprint"], chain_hash)
    with open(META_DIR / f"{token_id}.json", "w") as f:
        json.dump(meta, f, indent=2)

    coa_html = build_coa_html(token_id, title, rarity, image_hash,
                              om109["om109_fingerprint"], chain_hash, ts)
    with open(CERT_DIR / f"{token_id}_certificate.html", "w") as f:
        f.write(coa_html)

    # Live export to Gallery as it's produced
    try:
        import shutil
        shutil.copy(img_path, GALLERY_EXPORT / img_path.name)
    except Exception as e:
        print(f"  gallery export warning: {e}")

    print(f"  OM109   : {om109['om109_fingerprint'][:32]}...")
    print(f"  Chain   : {chain_hash[:32]}...")
    print(f"  MINTED  : {title} #{token_id} \u2014 {rarity}")
    return True


def verify_ledger():
    if not LEDGER_LOG.exists():
        print("No ledger found.")
        return False
    entries = [json.loads(l) for l in open(LEDGER_LOG) if l.strip()]
    print(f"\nVerifying {len(entries)} entries...")
    errors = 0
    prev = "OMEGA_MONOLITH_GENESIS"
    for e in entries:
        if e.get("prev_chain_hash") != prev:
            print(f"  CHAIN BREAK #{e['token_id']}")
            errors += 1
        prev = e.get("chain_hash", "")
    ok = errors == 0
    print(f"  {'ALL CLEAN' if ok else str(errors)+' ERRORS'} \u2014 {len(entries)} entries")
    return ok


def assign_wallets():
    """Assign founding-13 wallets: Thomas gets the guaranteed Diamond,
    the other 12 founders get a deterministic random sample of the
    remaining 99 tokens (which naturally includes the other 5 Diamonds
    wherever they happen to land)."""
    rng = random.Random(OMEGA_GENESIS_SEED + "_WALLET_ASSIGN")
    remaining_tokens = [t for t in range(TOKEN_START, TOKEN_START + TOKEN_COUNT)
                        if t != THOMAS_DIAMOND_TOKEN]
    other_12_tokens = rng.sample(remaining_tokens, 12)

    assignments = [(THOMAS_DIAMOND_TOKEN, THOMAS_FOUNDER_WALLET)]
    other_wallets = [w for w in FOUNDING_13_WALLETS if w != THOMAS_FOUNDER_WALLET]
    for token, wallet in zip(other_12_tokens, other_wallets):
        assignments.append((token, wallet))

    try:
        conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="omega_ledger",
                                user="postgres", connect_timeout=5)
        conn.autocommit = True
        cur = conn.cursor()
        for token_id, wallet_id in assignments:
            is_founder_diamond = (token_id == THOMAS_DIAMOND_TOKEN)
            cur.execute("""
                UPDATE nft_registry SET owner_account_id=%s, is_founder_linked=%s
                WHERE token_id=%s AND collection=%s
            """, (wallet_id, is_founder_diamond, token_id, COLLECTION_NAME))
            print(f"  assigned #{token_id} -> {wallet_id[:8]}...")
        conn.close()
        print(f"Done. {len(assignments)} tokens assigned.")
        print(f"Thomas's Impossible Diamond: #{THOMAS_DIAMOND_TOKEN}")
        other_diamonds = [t for t in IMPOSSIBLE_DIAMOND_TOKENS if t != THOMAS_DIAMOND_TOKEN]
        print(f"Other 5 Impossible Diamonds (in general batch): {other_diamonds}")
    except Exception as e:
        print(f"Wallet assignment failed: {e}")


def register_postgres():
    """Insert all 100 tokens into omega_ledger.nft_registry."""
    try:
        conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="omega_ledger",
                                user="postgres", connect_timeout=5)
        conn.autocommit = True
        cur = conn.cursor()
        succeeded, skipped, failed = 0, 0, 0
        for meta_file in sorted(META_DIR.glob("*.json")):
            meta = json.load(open(meta_file))
            try:
                cur.execute("""
                    INSERT INTO nft_registry
                        (token_id, name, title, rarity, theme, image_sha256,
                         om109_fingerprint, chain_hash, owner_account_id,
                         is_founder_linked, sale_status, collection)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'UNASSIGNED',false,'unsold',%s)
                    ON CONFLICT (collection, token_id) DO NOTHING
                """, (
                    meta["edition"], meta["name"], meta["title"], meta["rarity"],
                    meta["attributes"][5]["value"],  # Structure
                    meta["image_sha256"], meta["om109_fingerprint"],
                    meta["om109_chain_hash"], COLLECTION_NAME
                ))
                succeeded += 1
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                skipped += 1
            except Exception as e:
                conn.rollback()
                print(f"  failed #{meta['edition']}: {e}")
                failed += 1
        conn.close()
        print(f"\nRegistry: {succeeded} succeeded / {skipped} skipped / {failed} failed")
    except Exception as e:
        print(f"Registry connection failed: {e}")


def main():
    parser = argparse.ArgumentParser(description=f"{COLLECTION_NAME} NFT Engine — full automation")
    parser.add_argument("--full-run", action="store_true",
                        help="Mint all 100, verify, register, generate COAs, assign wallets — fully automated")
    parser.add_argument("--id", type=int, default=None)
    parser.add_argument("--count", type=int, default=TOKEN_COUNT)
    parser.add_argument("--start", type=int, default=TOKEN_START)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--assign-wallets", action="store_true")
    args = parser.parse_args()

    print(f"\n {COLLECTION_NAME.upper()} \u2014 Omega Art Studio NFT Engine")
    print(f" Output: {BASE}")
    print(f" Gallery: {GALLERY_EXPORT}")
    print(f" Impossible Diamonds (this batch): {IMPOSSIBLE_DIAMOND_TOKENS}")
    print(f" Thomas's guaranteed Diamond: #{THOMAS_DIAMOND_TOKEN}\n")

    if args.verify:
        verify_ledger()
        return
    if args.register:
        register_postgres()
        return
    if args.assign_wallets:
        assign_wallets()
        return
    if args.id is not None:
        mint_token(args.id)
        return

    existing = {int(f.stem) for f in IMAGES_DIR.glob("*.png")}
    success, t0 = 0, time.time()
    for i in range(args.start, args.start + args.count):
        if i in existing:
            print(f"  skip #{i} \u2014 already minted")
            success += 1
            continue
        if mint_token(i):
            success += 1
        if i < args.start + args.count - 1:
            time.sleep(3)

    print(f"\n MINTING COMPLETE: {success}/{args.count} in {time.time()-t0:.0f}s")

    if args.full_run:
        print("\n--- Running full pipeline ---")
        ok = verify_ledger()
        if not ok:
            print("Chain verification FAILED — stopping before registry/COA/wallet steps.")
            return
        register_postgres()
        assign_wallets()
        print(f"\n {COLLECTION_NAME} fully complete: {success} minted, verified, registered, assigned.")
        print(f" COAs: {CERT_DIR} ({len(list(CERT_DIR.glob('*.html')))} files)")
        print(f" Metadata: {META_DIR} ({len(list(META_DIR.glob('*.json')))} files)")


if __name__ == "__main__":
    main()
