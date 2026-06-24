#!/usr/bin/env python3
"""
SOMNIUM — 100-piece surrealist fine-art generative NFT collection
by Thomas Lee Harvey | Omega AI | OM109 Authenticated
"""
import hashlib, json, random, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import quote
try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
    PIL_OK = True
except:
    PIL_OK = False

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE        = Path.home() / "somnium"
IMAGES_DIR  = BASE / "images"
META_DIR    = BASE / "metadata"
LEDGER_LOG  = BASE / "om109_ledger.jsonl"
STATUS_FILE = BASE / "mint_status.json"   # live dashboard feed
for d in [IMAGES_DIR, META_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────────
COLLECTION        = "Somnium"
CREATOR           = "Thomas Lee Harvey"
TOTAL_SUPPLY      = 100
GENESIS_SEED      = "OMEGA_GENESIS_THOMAS_LEE_HARVEY_SOMNIUM_2026"
WALLET_SEED       = "OMEGA_SOMNIUM_WALLET_ASSIGN_2026"
THOMAS_WALLET     = "2109a4cc-a066-4698-a478-a786bf096318"
_LAST_CHAIN_HASH  = "SOMNIUM_GENESIS"

# ── 5 Impossible Diamond tokens (deterministic) ────────────────────────────────
_imp_rng = random.Random(GENESIS_SEED + "_IMPOSSIBLE")
IMPOSSIBLE_TOKENS = sorted(_imp_rng.sample(range(1, 101), 5))

# ── Surrealist content — ALL NEW, nothing from Echoes of Eternity ──────────────
SURREAL_TITLES = [
    "Anamnesis","Apricity","Axiom","Bewilderment","Brine","Caesura","Chiaroscuro",
    "Cinders","Coalescence","Contrail","Dusk","Elegy","Evanescence","Exhalation",
    "Fathom","Filament","Fracture","Fugue","Gossamer","Gravity","Halcyon","Haze",
    "Hollow","Hypothesis","Impasse","Inception","Inkblot","Interval","Iridescence",
    "Isthmus","Kindling","Labyrinth","Lacework","Latency","Limen","Luminance",
    "Meridian","Miasma","Monolith","Murmur","Nadir","Nebula","Nimbus","Nocturne",
    "Obscura","Omission","Oscillation","Palimpsest","Parallax","Penumbra","Phosphene",
    "Precipice","Prism","Quietude","Rapture","Remnant","Resonance","Rift","Rupture",
    "Sediment","Seepage","Shimmer","Silence","Slipstream","Solitude","Sonance",
    "Specter","Splinter","Static","Stratum","Sublimation","Suspension","Tenebre",
    "Threshold","Tide","Tinder","Torque","Trace","Tremor","Twilight","Undertow",
    "Unmooring","Updraft","Vapour","Vestige","Void","Vortex","Wavelength","Wither",
    "Xenolith","Yearning","Zenith","Zephyr","Abeyance","Aloft","Atrophy","Aureole",
    "Bloom","Breach"
]

# (shadow_object, foreground_subject, accent_color)
CONCEPTS = [
    ("a burning library","a single unburnt page folded into a paper crane","ash white and ember gold"),
    ("a collapsing bridge","a child's shoe balanced on a stone","fog grey"),
    ("a whale in mid-air","a fisherman's hook with no line","deep ocean cobalt"),
    ("a melting clock tower","a pocket watch frozen at midnight","tarnished brass"),
    ("a flock of birds flying backwards","a single feather nailed to wood","storm petrel grey"),
    ("a lighthouse with no beam","a moth circling empty air","bioluminescent green"),
    ("a forest of upside-down trees","a single root holding a teardrop of soil","earth umber"),
    ("a cathedral made of ice","a single lit match","glacial blue with one orange flame"),
    ("a locomotive emerging from a wall","a ticket to nowhere, creased and torn","soot black"),
    ("a mountain range seen through a keyhole","a key with no teeth","granite and rust"),
    ("a staircase descending into the sky","a shoe on the topmost step","cloud white"),
    ("a river flowing uphill","a single stone hovering above still water","slate and mist"),
    ("a giant hand reaching through fog","a glove with no hand inside","pale ivory"),
    ("a city inverted in a raindrop","a glass orb reflecting a different world","refraction gold"),
    ("a clock with no hands","a sundial in a windowless room","shadow charcoal"),
    ("a door standing in an open field","a key melting like wax","oxidised copper"),
    ("a skeleton of a ship on dry land","a compass pointing inward","barnacle and verdigris"),
    ("a telescope aimed at the ground","a buried star, barely glowing","midnight indigo"),
    ("a pair of wings casting the shadow of a cage","a feather locked in amber","captured amber"),
    ("a mirror reflecting a different room","a portrait with the face removed","silver and void"),
    ("a giant ear listening to silence","a single tuning fork vibrating in still air","resonance bronze"),
    ("a throne made of driftwood","a crown of dried seaweed","sea-bleached ivory"),
    ("a book whose pages are blank mirrors","a pen with no ink","reflective silver"),
    ("a chandelier of bones","a single white candle extinguished","bone and smoke"),
    ("a map of an undiscovered country","a compass spinning endlessly","cartographic sepia"),
    ("an hourglass with sand flowing upward","a single grain suspended at the midpoint","amber sand"),
    ("a piano with no keys","a single musical note floating in air","ebony and resonance gold"),
    ("a window looking onto itself","a frame with no canvas","threshold white"),
    ("a tree growing downward from the ceiling","a single apple resting on the floor","inverted green"),
    ("a sundial casting moonlight","a shadow that points north","silver and dark earth"),
    ("a figure made entirely of smoke","a cigarette still burning, holder absent","smoke and ember"),
    ("a locked box with no keyhole","a key dissolving into light","tarnished gold"),
    ("a telescope full of fog","an eye pressed to a keyhole","lens grey"),
    ("a crown with no head beneath it","a single jewel rolling on marble","imperial crimson"),
    ("a hammer striking water","ripples frozen mid-explosion","mercury and wave"),
    ("a cage full of open air","a single lock with no hasp","wrought iron and sky"),
    ("a ship's anchor floating upward","a length of chain curled like a sleeping dog","verdigris"),
    ("a violin with no strings","a bow moving through air","lacquered rosewood"),
    ("a labyrinth seen from above, solved","a single thread leading out","limestone and thread"),
    ("a bell that casts silence","a clapper never touching bronze","patina green"),
    ("a gramophone playing absence","a vinyl record frozen mid-spin","shellac black"),
    ("a ladder leaning against open sky","a single rung lying on the ground","weathered teak"),
    ("a chair floating six inches above the floor","a shadow pinned beneath it","ash and void"),
    ("a surgeon's table with a perfect outline","surgical tools arranged but untouched","clinical white"),
    ("a typewriter with keys removed","a single typed word on blank paper","ink and chrome"),
    ("a prison cell with walls of light","a shadow locked inside","cell grey"),
    ("a compass pointing to itself","a map with only one location marked","cartographic crimson"),
    ("a dress standing upright, wearer absent","a single button on the floor","dress silk ivory"),
    ("a glass of water evaporating upward","the wet ring left on the table","water blue"),
    ("a pair of hands in prayer casting a shadow of fists","a single rosary bead","devotion gold"),
    ("a bonfire made of ice","smoke that is cold to the touch","glacial flame"),
    ("a telephone ringing in an empty room","a receiver off the hook, dangling","bakelite cream"),
    ("a painting of a window that opens","a drape moved by wind with no wind","canvas and breeze"),
    ("a sundial at midnight","a shadow with no sun to cast it","moonstone grey"),
    ("a microscope aimed at a galaxy","a single cell containing a universe","cosmic violet"),
    ("a thundercloud the size of a fist","lightning in a bottle, corked","storm copper"),
    ("a dam holding back a desert","a single grain of sand leaking through","sand and concrete"),
    ("a watch stopped at the moment of birth","a newborn's footprint in ash","birth white"),
    ("a blindfold casting the shadow of open eyes","a single tear on dry glass","sight silver"),
    ("a compass made of salt","a direction that dissolves","mineral white"),
    ("a shipwrecked compass still pointing true","barnacles over the N","shipwreck teal"),
    ("a lantern full of darkness","a moth flying away from light","lamp black"),
    ("a hive with no bees","a single honeycomb cell filled with shadow","honey gold"),
    ("a road that ends at its own beginning","a milestone reading zero","asphalt grey"),
    ("a crown of thorns casting a halo","a single drop of blood still falling","martyrdom crimson"),
    ("a wave frozen at its peak","a surfer's silhouette gone","sea foam"),
    ("a fire hydrant casting a flood","a single fish stranded on concrete","fire red"),
    ("a key cast in ice, melting","the lock it once opened, rusted shut","ice blue"),
    ("a balloon at the floor","a string pointing downward","cadmium red"),
    ("a diving board over a dry pool","a splash captured in concrete","pool aqua"),
    ("a sundial made of snow","a shadow outlasting the sun","winter white"),
    ("a magnifying glass burning nothing","a single ash fleck hovering","lens amber"),
    ("a snowglobe in a desert","the blizzard inside undisturbed","glass and sand"),
    ("a metronome at the speed of grief","a pendulum paused mid-swing","ebony and patience"),
    ("a gravestone for an idea","the epitaph unreadable","churchyard limestone"),
    ("a map folded wrong","a territory that doesn't fit its borders","parchment and error"),
    ("a fingerprint made of smoke","the finger that made it absent","forensic grey"),
    ("a pair of scissors cutting light","a shadow split in two","blade silver"),
    ("an anchor made of clouds","the ship sunk below fog","cumulus white"),
    ("a hammer made of glass","a nail bent but unbroken","brittle clarity"),
    ("a net full of reflections","not a single fish","water silver"),
    ("a candle whose flame points down","wax dripping upward","inverted gold"),
    ("a window frame with no glass","wind passing through undisturbed","threshold grey"),
    ("a ladder made of water","each rung rippling underfoot","fluid teal"),
    ("a crown dissolving in rain","a single gem left in the puddle","rain and ruby"),
    ("a door knocker on a wall with no door","a welcome mat going nowhere","threshold oak"),
    ("a lighthouse on a mountain","a single ship in the clouds","summit white"),
    ("a telescope looking at yesterday","the image still sharp","sepia and glass"),
    ("a safe with no combination","a dial spinning of its own accord","vault steel"),
    ("a broken compass still spinning","magnetic north in dispute","lodestone grey"),
    ("a chandelier at the bottom of a pool","light rising through water","submerged crystal"),
    ("a clock face with numbers counted backward","the hands moving forward anyway","time copper"),
    ("a blindfold made of mirrors","reflecting only what you fear to see","fear silver"),
    ("a pair of footprints going nowhere","the walker invisible but present","dust and path"),
    ("a bottle containing a storm","lightning visible through the glass","storm bottle blue"),
    ("a cage containing a shadow","the creature gone, the darkness remaining","iron and absence"),
    ("a compass made of bone","pointing at the body it came from","osseous white"),
    ("a throne of melting ice","the crown already gone","thaw silver"),
]

ENVIRONMENTS = [
    "on polished jet-black marble under a single cold spotlight from directly above",
    "on rough-poured concrete, industrial tungsten light raking from the right at 15 degrees",
    "on aged white linen, soft box diffusion, shadowless fill except the subject shadow",
    "on weathered oak floorboards, warm amber key light from behind left",
    "on frosted tempered glass surface, backlit from below with cool daylight white",
    "on dark charcoal stone, twin hard lights from opposing angles creating mirror shadows",
    "on a perfectly still sheet of water, one millimetre deep, reflecting everything",
    "on oxidised copper plate, single bare-bulb warm light from directly right",
    "on matte white seamless paper, soft natural north-facing studio window light",
    "on brushed gunmetal steel, fluorescent blue-white overhead bars",
]

DROPLET_STYLES = [
    "surface covered in heavy photorealistic water droplets with full internal light refraction",
    "beaded with mercury-like perfectly spherical droplets catching every light source",
    "dripping with slow crystalline dew, each drop a miniature wide-angle lens",
    "wrapped in a thin tension-held film of water, surface tension visible at the edges",
    "dusted with micro-condensation, thousands of tiny droplets diffracting light into spectra",
]

# ── Rarity ─────────────────────────────────────────────────────────────────────
def get_rarity(token_id):
    if token_id in IMPOSSIBLE_TOKENS:
        return "Impossible Diamond", 6
    random.seed(token_id * 8147 + 31337)   # different multiplier from Echoes
    r = random.random()
    if r < 0.03:  return "Black Diamond", 5
    elif r < 0.08: return "Super Rare", 4
    elif r < 0.25: return "Rare", 3
    elif r < 0.55: return "Medium", 2
    else:          return "Common", 1

def get_title(token_id):
    random.seed(token_id * 4561 + 2026)    # different multiplier from Echoes
    return SURREAL_TITLES[int(random.random() * len(SURREAL_TITLES))]

# ── Prompt ─────────────────────────────────────────────────────────────────────
def build_prompt(token_id, complexity):
    random.seed(token_id * 6271 + complexity)
    concept     = CONCEPTS[(token_id - 1) % len(CONCEPTS)]
    shadow_desc, subject_desc, color_desc = concept
    env         = ENVIRONMENTS[token_id % len(ENVIRONMENTS)]
    droplets    = DROPLET_STYLES[token_id % len(DROPLET_STYLES)]
    perspective = ["eye-level straight-on","slightly elevated three-quarter","low angle looking up","bird's eye directly overhead"][token_id % 4]
    prompt = (
        f"Fine art surrealist studio photography, hyperrealistic, 12k resolution, {perspective}. "
        f"Full frame composition filling entire image edge to edge, no black borders, no vignette. "
        f"{env}. "
        f"Enormous dramatic shadow of {shadow_desc} cast hard across the background, "
        f"the object casting this shadow is completely and utterly absent from the scene. "
        f"Centered in the foreground: {subject_desc}, {droplets}, "
        f"vivid saturated {color_desc} — the sole source of colour in an otherwise monochrome scene. "
        f"Medium format film photography aesthetic, tack-sharp subject, dissolved background, "
        f"René Magritte and Francesca Woodman surrealist fine art, collector NFT, museum quality, "
        f"no text, no watermark, no signature visible."
    )
    negative = (
        "text, watermark, signature, logo, border, frame, vignette, letterbox, black bars, "
        "multiple subjects, busy background, chromatic aberration, noise, grain, blurry, "
        "oversaturated, cartoon, illustration, painting, digital art, CGI obvious, ugly"
    )
    return prompt, negative, concept

# ── Image generation ───────────────────────────────────────────────────────────
def generate_image(token_id, prompt, negative, complexity):
    steps   = {1:20, 2:25, 3:30, 4:35, 5:40, 6:50}.get(complexity, 25)
    seed    = token_id * 251 + complexity + 20260618   # different offset from Echoes
    out_path = IMAGES_DIR / f"{token_id:04d}.png"
    url = (
        f"https://image.pollinations.ai/prompt/{quote(prompt)}"
        f"?width=768&height=1024&seed={seed}&steps={steps}"
        f"&negative={quote(negative)}&model=flux&nologo=true&enhance=true"
    )
    print(f"  generating #{token_id:04d} ({steps} steps)...")
    for attempt in range(1, 4):
        try:
            with urlopen(Request(url, headers={"User-Agent": "SomniumNFT/1.0"}), timeout=150) as r:
                data = r.read()
            if PIL_OK:
                from io import BytesIO
                img = Image.open(BytesIO(data)).convert("RGB")
                # autocrop black bars
                import numpy as np
                arr = np.array(img.convert("L"))
                row_max = arr.max(axis=1)
                non_black = np.where(row_max > 15)[0]
                if len(non_black) > 10:
                    img = img.crop((0, non_black[0], img.width, non_black[-1]+1))
                # enhance
                img = ImageEnhance.Contrast(img).enhance(1.15)
                img = ImageEnhance.Color(img).enhance(1.25)
                img = ImageEnhance.Sharpness(img).enhance(1.3)
                img = img.resize((768, 1024), Image.LANCZOS)
                img.save(out_path, optimize=True, quality=99)
            else:
                with open(out_path, "wb") as f:
                    f.write(data)
            print(f"  saved {out_path.name} ({len(data)//1024}KB)")
            return out_path, url
        except Exception as e:
            print(f"  attempt {attempt}/3: {e}")
            if attempt < 3:
                time.sleep(12 * attempt)
    return None, url

# ── OM109 signing ──────────────────────────────────────────────────────────────
def om109_sign(token_id, image_hash):
    genesis = hashlib.sha256(GENESIS_SEED.encode()).hexdigest()
    sig_a   = hashlib.sha256(f"{genesis}:A:{token_id}:{image_hash}".encode()).hexdigest()
    sig_b   = hashlib.sha256(f"{genesis}:B:{token_id}:{image_hash}:{sig_a}".encode()).hexdigest()
    fp      = hashlib.sha256(f"{sig_a[:32]}{sig_b[:32]}".encode()).hexdigest()
    return {"sig_a": sig_a, "sig_b": sig_b, "om109_fingerprint": fp}

# ── JSONL ledger ───────────────────────────────────────────────────────────────
def ledger_mint_jsonl(token_id, image_hash, om109, rarity, shadow_desc, title, ts):
    global _LAST_CHAIN_HASH
    if LEDGER_LOG.exists():
        lines = [l for l in LEDGER_LOG.read_text().splitlines() if l.strip()]
        if lines:
            _LAST_CHAIN_HASH = json.loads(lines[-1]).get("chain_hash", _LAST_CHAIN_HASH)
    entry = {
        "event_type": "NFT_MINT", "token_id": token_id,
        "collection": COLLECTION, "creator": CREATOR,
        "title": title, "image_sha256": image_hash,
        "rarity": rarity, "theme": shadow_desc,
        "om109_fingerprint": om109["om109_fingerprint"],
        "sig_a": om109["sig_a"], "sig_b": om109["sig_b"],
        "minted_at": ts, "prev_chain_hash": _LAST_CHAIN_HASH,
    }
    entry["chain_hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
    _LAST_CHAIN_HASH = entry["chain_hash"]
    with open(LEDGER_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry["chain_hash"]

# ── Postgres mirror ────────────────────────────────────────────────────────────
def ledger_mint_psql(token_id, image_hash, om109, rarity, title, chain_hash):
    try:
        import psycopg2
        conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="omega_bank",
                                user="postgres", connect_timeout=5)
        conn.autocommit = True
        cur = conn.cursor()
        idem = hashlib.sha256(f"SOMNIUM_MINT:{token_id}:{image_hash}".encode()).hexdigest()[:32]
        cur.execute(
            "INSERT INTO ledger_entries "
            "(transaction_id,wallet_id,event_type,amount,direction,debit_account,credit_account,"
            "memo,idempotency_key,om109_fingerprint,chain_hash) "
            "VALUES (uuid_generate_v4(),'2db2e016-f6a1-4086-bec2-363edfb1c26b',%s,1.00,'CREDIT',"
            "'somnium_collection','omega_treasury',%s,%s,%s,%s) ON CONFLICT(idempotency_key) DO NOTHING",
            (f"SOMNIUM_MINT_{rarity.upper().replace(' ','_')}",
             f"SOMNIUM #{token_id:04d} '{title}' {rarity} | SHA256:{image_hash[:16]}",
             idem, om109["om109_fingerprint"], chain_hash)
        )
        conn.close()
        print(f"  ledger PSQL: recorded #{token_id:04d}")
    except Exception as e:
        print(f"  ledger PSQL: offline ({e}) — JSONL only")

# ── Metadata ───────────────────────────────────────────────────────────────────
def build_metadata(token_id, rarity, title, shadow_desc, subject_desc, color_desc,
                   image_hash, om109_fp, chain_hash, pollinations_url):
    is_signed = rarity in ("Impossible Diamond", "Black Diamond")
    palette = ["Void Monochrome","Lucid Grey","Phantom Chrome","Obsidian Dream","Liminal Silver"][token_id % 5]
    return {
        "name": f"Somnium — Unique #{token_id:04d}" if rarity == "Impossible Diamond"
                else f"Somnium — {title} #{token_id:04d}",
        "description": (
            f"\"{title}\" is a 1-of-100 surrealist fine art NFT from the Somnium collection "
            f"by Thomas Lee Harvey. "
            f"The shadow of {shadow_desc} dominates a monochrome world, "
            f"cast by something entirely absent from the scene. "
            f"The only colour belongs to {subject_desc}. "
            f"Every token is authenticated by OM109 alternating dual-key signature. "
            f"Rarity: {rarity}. Edition {token_id} of {TOTAL_SUPPLY}."
        ),
        "image": pollinations_url,
        "image_local": f"images/{token_id:04d}.png",
        "collection": COLLECTION,
        "creator": CREATOR,
        "rarity": rarity,
        "title": "Unique" if rarity == "Impossible Diamond" else title,
        "token_id": token_id,
        "total_supply": TOTAL_SUPPLY,
        "image_sha256": image_hash,
        "om109_fingerprint": om109_fp,
        "om109_chain_hash": chain_hash,
        "authentication": "OM109 Alternating Dual-Key Signature",
        "attributes": [
            {"trait_type": "Rarity",             "value": rarity},
            {"trait_type": "Title",              "value": "Unique" if rarity == "Impossible Diamond" else title},
            {"trait_type": "Edition",            "value": f"{token_id} of {TOTAL_SUPPLY}"},
            {"trait_type": "Creator",            "value": CREATOR},
            {"trait_type": "Collection",         "value": COLLECTION},
            {"trait_type": "Style",              "value": "Hyper-Surrealist Fine Art Photography"},
            {"trait_type": "Phantom Shadow",     "value": shadow_desc},
            {"trait_type": "Color Subject",      "value": subject_desc[:60]},
            {"trait_type": "Accent Color",       "value": color_desc},
            {"trait_type": "Color Palette",      "value": palette},
            {"trait_type": "Authentication",     "value": "OM109 Dual-Signature"},
            {"trait_type": "SHA256 Fingerprint", "value": image_hash},
            {"trait_type": "Signed by Artist",   "value": "Yes" if is_signed else "No"},
            {"trait_type": "Impossible Diamond", "value": "Yes" if rarity == "Impossible Diamond" else "No"},
        ]
    }

# ── Status file (live dashboard feed) ─────────────────────────────────────────
def write_status(minted, total, current_token, current_title, current_rarity, errors):
    status = {
        "minted": minted, "total": total,
        "current_token": current_token,
        "current_title": current_title,
        "current_rarity": current_rarity,
        "errors": errors,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "impossible_tokens": IMPOSSIBLE_TOKENS,
    }
    STATUS_FILE.write_text(json.dumps(status, indent=2))

# ── Main mint loop ─────────────────────────────────────────────────────────────
def mint_token(token_id):
    rarity, complexity = get_rarity(token_id)
    title              = get_title(token_id)
    ts                 = datetime.now(timezone.utc).isoformat()
    prompt, negative, concept = build_prompt(token_id, complexity)
    shadow_desc, subject_desc, color_desc = concept

    print(f"\n{'═'*55}")
    print(f"  #{token_id:04d} '{title}' [{rarity}]")
    print(f"  Shadow : {shadow_desc[:60]}")
    print(f"  Subject: {subject_desc[:60]}")
    print(f"  Color  : {color_desc}")
    print(f"{'═'*55}")

    img_path, poll_url = generate_image(token_id, prompt, negative, complexity)
    if not img_path:
        print(f"  ERROR: image generation failed for #{token_id:04d}")
        return False

    image_hash = hashlib.sha256(img_path.read_bytes()).hexdigest()
    om109      = om109_sign(token_id, image_hash)
    chain_hash = ledger_mint_jsonl(token_id, image_hash, om109, rarity, shadow_desc, title, ts)
    ledger_mint_psql(token_id, image_hash, om109, rarity, title, chain_hash)
    meta = build_metadata(token_id, rarity, title, shadow_desc, subject_desc, color_desc,
                          image_hash, om109["om109_fingerprint"], chain_hash, poll_url)
    with open(META_DIR / f"{token_id:04d}.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"  OM109  : {om109['om109_fingerprint'][:32]}...")
    print(f"  Chain  : {chain_hash[:32]}...")
    if rarity == "Impossible Diamond":
        print(f"  ★ IMPOSSIBLE DIAMOND ★  Token #{token_id:04d}")
    print(f"  ✓ MINTED: {title} #{token_id:04d} — {rarity}")
    return True

def main():
    if "--verify" in sys.argv:
        if not LEDGER_LOG.exists():
            print("No ledger found."); return
        entries = [json.loads(l) for l in LEDGER_LOG.read_text().splitlines() if l.strip()]
        prev = "SOMNIUM_GENESIS"
        ok = 0
        for e in entries:
            check = dict(e); stored = check.pop("chain_hash")
            expected = hashlib.sha256(json.dumps(check, sort_keys=True).encode()).hexdigest()
            if expected != stored or e.get("prev_chain_hash") != prev:
                print(f"CHAIN BREAK at token #{e['token_id']}"); return
            prev = stored; ok += 1
        print(f"ALL CLEAN — {ok} entries verified")
        return

    print(f"\n{'═'*55}")
    print(f"  SOMNIUM — Thomas Lee Harvey")
    print(f"  Impossible Diamond tokens: {IMPOSSIBLE_TOKENS}")
    print(f"{'═'*55}\n")

    minted = 0; errors = []
    write_status(0, TOTAL_SUPPLY, 0, "", "", [])

    for token_id in range(1, TOTAL_SUPPLY + 1):
        rarity, _ = get_rarity(token_id)
        title = get_title(token_id)
        write_status(minted, TOTAL_SUPPLY, token_id, title, rarity, errors)
        ok = mint_token(token_id)
        if ok:
            minted += 1
        else:
            errors.append(token_id)
        write_status(minted, TOTAL_SUPPLY, token_id, title, rarity, errors)

    print(f"\n{'═'*55}")
    print(f"  SOMNIUM COMPLETE: {minted}/100 minted")
    if errors: print(f"  Failed tokens: {errors}")
    print(f"{'═'*55}")
    write_status(minted, TOTAL_SUPPLY, 0, "COMPLETE", "", errors)

if __name__ == "__main__":
    main()

