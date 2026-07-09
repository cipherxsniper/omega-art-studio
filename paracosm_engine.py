#!/usr/bin/env python3
import hashlib, json, random, sys, time, subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import quote
try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
    PIL_OK = True
except ImportError:
    PIL_OK = False

BASE        = Path.home() / "paracosm"
IMAGES_DIR  = BASE / "images"
META_DIR    = BASE / "metadata"
LEDGER_LOG  = BASE / "om109_ledger.jsonl"
STATUS_FILE = BASE / "mint_status.json"
GALLERY_DIR = Path("/sdcard/Pictures/Paracosm")
for d in [IMAGES_DIR, META_DIR, GALLERY_DIR]:
    d.mkdir(parents=True, exist_ok=True)

COLLECTION   = "Paracosm"
CREATOR      = "Thomas Lee Harvey"
TOTAL_SUPPLY = 100
TOKEN_OFFSET = 1000
GENESIS_SEED = "OMEGA_GENESIS_THOMAS_LEE_HARVEY_PARACOSM_2026"
_LAST_CHAIN_HASH = "PARACOSM_GENESIS"

_imp_rng = random.Random(GENESIS_SEED + "_IMPOSSIBLE")
IMPOSSIBLE_TOKENS = sorted(_imp_rng.sample(range(TOKEN_OFFSET+1, TOKEN_OFFSET+101), 5))

CONCEPTS = [
    ("a staircase that spirals upward into itself, Escher-impossible, steps connecting to their own beginning","a single bright red apple resting impossibly on the topmost step, droplets of water catching the light","vivid crimson red"),
    ("a cathedral built entirely from suspended water, walls made of frozen falling rain","a golden pocket watch hanging mid-air, ticking, dripping with condensation","molten gold"),
    ("a bridge that folds back over itself in a Mobius loop, walkable on both sides simultaneously","a single teal glass orb resting at the exact center of the twist, beaded with dew","deep teal"),
    ("a city skyline growing downward from the clouds, skyscrapers rooted in sky reaching toward ground","one electric blue lantern glowing inside an otherwise dark inverted tower","electric blue"),
    ("a library where the books are the architecture, shelves made of compressed solidified pages","one violet crystal orb glowing with internal light, sitting on an open book","violet luminance"),
    ("a house where every room is the same room from a different impossible angle, walls repeating infinitely","a single orange ceramic vase, the only object staying still across all the angles","burnt orange"),
    ("a waterfall flowing upward into the sky, gravity reversed only for the water","a single coral-colored koi fish suspended mid-leap against the current","coral pink"),
    ("a forest where the trees grow as architecture, trunks forming archways and doorframes","a single emerald green hummingbird frozen mid-flight, wings a blur of color","emerald green"),
    ("a clocktower where every face shows a different impossible time, hands spinning opposite directions","a single brass pendulum swinging against the room's gravity, polished and gleaming","brass copper"),
    ("a spiral staircase descending into the sky instead of the ground, steps vanishing into clouds above","a single pale silver feather falling upward past the steps, catching the light","pale silver"),
    ("a room where floor and ceiling have swapped, furniture bolted upside-down","a crystal white chandelier reaching up from what should be the floor, glittering","crystal white"),
    ("a corridor that telescopes infinitely backward and forward at once, doors receding to vanishing points","a single antique brass key floating at the one fixed point in the corridor","antique brass"),
    ("a mountain range carved entirely from glass, peaks transparent revealing storms trapped inside","a single storm-grey bird flying through the glass mountain unharmed","storm grey"),
    ("an ocean standing as a vertical wall, waves frozen mid-crash but defying gravity entirely","a sea-foam cyan lighthouse beam cutting horizontally through the standing wave","sea foam cyan"),
    ("a staircase made of falling dominoes, each step frozen at the exact moment of toppling","a single ivory white marble rolling uphill against the fall, glossy and perfect","ivory white"),
    ("a town square where every building leans toward a different impossible center of gravity","a single warm gold street lamp standing perfectly vertical against all the leaning","warm gaslight gold"),
    ("a tunnel looping through itself like a Klein bottle, entrance and exit the same point seen twice","a single bright white headlight beam approaching from both directions at once","headlight white"),
    ("a garden where flowers grow from the sky downward, roots reaching up into clouds","a single honeycomb-gold bee flying upside-down relative to the flowers","honeycomb gold"),
    ("a pier extending into a sky-ocean, the horizon line vertical instead of horizontal","a deep navy fishing line dangling sideways into the vertical horizon, glistening","deep navy"),
    ("a room built from stacked impossible triangles, a Penrose structure made habitable","a single red sphere rolling along an impossible always-downhill path","vivid red"),
    ("a chapel where pews face every wall simultaneously, perspective folding in on itself","a single amber candle flame bending toward all four walls at once","candlelight amber"),
    ("a skyscraper that is also its own mirrored reflection, seamless glass","a single mirror-silver bird flying into the seam where building meets reflection","mirror silver"),
    ("a staircase spiraling both up and down simultaneously from the same step, Penrose stairs made real","a single charcoal-grey shadow climbing the opposite direction from its owner","shadow charcoal"),
    ("a vineyard growing on vertical cliffs curving overhead into a full loop, gravity pulling toward center","a single wine-burgundy grape falling sideways toward the loop's core, glistening with juice","wine burgundy"),
    ("a marketplace where every stall roof is the floor of the stall above, an impossible Escher loop","a single apple-red apple resting on what should be empty air","apple red"),
    ("a bell tower where the bell hangs in four places at once, multiple impossible exposures","a single bronze-patina rope leading to only one of the four bells","bronze patina"),
    ("a hallway of doors opening onto each other infinitely, a recursive corridor","a single porcelain-toned hand reaching through from the furthest visible door","porcelain skin tone"),
    ("a frozen waterfall flowing in a complete vertical circle, water endlessly falling into itself","a single glacier-blue leaf caught perpetually circling within the loop","glacier blue"),
    ("a courtyard where four staircases each lead to the others beginnings, infinite Escher loop","a single lantern-gold lamp hanging at the courtyard's impossible center, glowing warm","lantern gold"),
    ("a cliffside town built into the underside of a floating landmass, buildings hanging into open sky","one hearth-orange lit window glowing warm against the cold blue void below","hearth orange"),
]

ENVIRONMENT_TEXTURES = [
    "carved from pale travertine stone, texture catching raking studio light, photographically real",
    "built from aged weathered concrete, water-stained, beautifully imperfect, tack sharp detail",
    "constructed of dark volcanic basalt, sharp-edged and severe, hyper-detailed surface texture",
    "made of bleached driftwood, sea-worn silver-grey grain visible in crisp focus",
    "formed from polished black granite, mirror-sheen under single hard light, ultra crisp reflections",
    "built of rough-hewn limestone, ancient and monumental, every chisel mark visible",
    "made of frosted structural glass, light diffusing through every surface, photorealistic translucency",
    "carved from pale sandstone, sun-bleached, wind-smoothed grain in full detail",
    "constructed of oxidized weathering steel, rust-orange texture rendered with total photographic accuracy",
    "made of white Carrara marble, veined and luminous, every vein crisply rendered",
]

LIGHTING_STYLES = [
    "single hard key light from upper left, dramatic theatrical studio lighting",
    "soft overcast diffusion, shadowless and quietly surreal, even illumination",
    "golden hour side light raking across every impossible surface, warm and crisp",
    "cold blue moonlight, deep shadows and silver highlights, high contrast",
    "twin opposing spotlights creating impossible double shadows, dramatic",
    "diffused studio softbox from directly above, museum-quality flat even light",
    "warm tungsten practical lighting from within the structure itself, glowing",
    "stormlight breaking through unseen clouds, dramatic and ominous",
    "bioluminescent ambient glow with no visible source, otherworldly",
    "harsh midday sun, every edge razor sharp, maximum contrast and clarity",
]

CAMERA_ANGLES = [
    "extreme wide-angle establishing shot, the impossible structure dominating the frame, full bleed composition",
    "low angle looking dramatically upward, emphasizing impossible scale, full frame edge to edge",
    "high angle bird's eye view looking directly down, complete coverage of frame",
    "three-quarter angle revealing the structure's impossible internal logic, tightly composed",
    "symmetrical centered composition, perfectly balanced, filling the entire frame",
    "ground-level worm's eye view, structure looming overhead, no empty space at edges",
    "telephoto compression flattening the structure into abstract geometry, full frame",
    "close detail shot filling the entire image with the impossible structure's texture",
]

SURREAL_TITLES = ["Vertigo","Recursion","Escher","Klein","Penrose","Paradox","Infinitum","Lattice","Topology","Singularity","Fractal","Aporia","Tessellate","Liminality","Vortex","Helix","Mobius","Cascade","Disquiet","Unravel","Folding","Bifurcation","Dimension","Aberration","Distortion","Warp","Chimera","Labyrinth","Geodesic","Tangent","Apex","Threshold","Apogee","Nadir","Hypostasis","Eidolon","Catacomb","Spire","Vault","Cantilever","Buttress","Arcology","Megastructure","Monolith","Citadel","Bastion","Rampart","Obelisk","Ziggurat","Colossus","Aperture","Convergence","Divergence","Anomaly","Causality","Continuum","Stratum","Echelon","Plinth","Cornice","Architrave","Pediment","Span","Truss","Keystone","Vaulting","Transept","Clerestory","Tessera","Quanta","Flux","Inversion","Refraction","Suspension","Equilibrium","Tension","Compression","Torque","Axis","Pivot","Fulcrum","Apexion","Zenith","Apsis","Perigee","Syzygy","Parallax","Horizon","Vanishing","Asymptote","Hyperbola","Manifold","Tesseract","Hypercube","Polytope","Crystalline","Geode","Stratagem","Edifice","Monument"]

def get_rarity(token_id):
    if token_id in IMPOSSIBLE_TOKENS: return "Impossible Diamond", 6
    random.seed(token_id*5347+9001)
    r=random.random()
    if r<0.03: return "Black Diamond",5
    elif r<0.08: return "Super Rare",4
    elif r<0.25: return "Rare",3
    elif r<0.55: return "Medium",2
    else: return "Common",1

def get_title(token_id):
    random.seed(token_id*6829+9001)
    return SURREAL_TITLES[int(random.random()*len(SURREAL_TITLES))]

def build_prompt(token_id, complexity):
    local_idx = token_id - TOKEN_OFFSET - 1
    random.seed(token_id*7919+complexity)
    concept = CONCEPTS[local_idx % len(CONCEPTS)]
    texture = ENVIRONMENT_TEXTURES[(local_idx*3+1) % len(ENVIRONMENT_TEXTURES)]
    lighting = LIGHTING_STYLES[(local_idx*7+2) % len(LIGHTING_STYLES)]
    angle = CAMERA_ANGLES[(local_idx*11+5) % len(CAMERA_ANGLES)]
    structure, physics, color = concept
    prompt = (
        f"Hyper-surrealist fine art photography, ultra-crisp hyperrealistic detail, {angle}. "
        f"Full frame composition filling the entire image completely, absolutely no black borders, no letterboxing, no empty margins. "
        f"{structure}, {texture}, {lighting}. "
        f"This is genuinely impossible architecture and physics rendered with total photographic realism, sharp and believable. "
        f"{physics}, rendered in bold vivid saturated {color} with visible water droplets and light refraction, "
        f"the single most striking point of color in an otherwise true-to-life desaturated grey-toned world. "
        f"Tack-sharp focus on the colored subject, soft dissolved background, "
        f"museum-quality architectural fine art photography, Gregory Crewdson cinematic lighting, "
        f"collector NFT, masterpiece, no text, no watermark, no signature."
    )
    negative = ("text, watermark, signature, logo, border, frame, vignette, letterbox, black bars, empty space, padding, "
                "cartoon, anime, illustration, painting, low quality, blurry, noise, grain, dull colors, washed out, "
                "multiple unrelated subjects, busy cluttered composition, deformed, ugly, amateur, cropped, cut off")
    return prompt, negative, concept

def push_to_gallery(img_path, token_id):
    try:
        dest = GALLERY_DIR / img_path.name
        dest.write_bytes(img_path.read_bytes())
        subprocess.run(["termux-media-scan", str(dest)], capture_output=True, timeout=10)
        print(f"  gallery: pushed {dest.name}")
    except Exception as e:
        print(f"  gallery sync failed: {e}")

def generate_image(token_id, prompt, negative, complexity):
    out_path = IMAGES_DIR / f"{token_id}.png"
    if out_path.exists(): return out_path, None
    steps = {1:30,2:35,3:40,4:45,5:55,6:70}.get(complexity,35)
    seed = token_id*311+complexity+20260619
    url = (f"https://image.pollinations.ai/prompt/{quote(prompt)}"
           f"?width=896&height=1152&seed={seed}&steps={steps}"
           f"&negative={quote(negative)}&model=flux&nologo=true&enhance=true")
    print(f"  generating #{token_id} ({steps} steps)...")
    for attempt in range(1,4):
        try:
            with urlopen(Request(url,headers={"User-Agent":"ParacosmNFT/1.0"}),timeout=160) as r:
                data=r.read()
            if PIL_OK:
                from io import BytesIO
                img=Image.open(BytesIO(data)).convert("RGB")
                img=ImageEnhance.Contrast(img).enhance(1.3)
                img=ImageEnhance.Color(img).enhance(1.5)
                img=ImageEnhance.Sharpness(img).enhance(1.5)
                img=img.filter(ImageFilter.SHARPEN)
                img.save(out_path,optimize=True,quality=99)
            else:
                out_path.write_bytes(data)
            print(f"  saved {out_path.name} ({len(data)//1024}KB)")
            return out_path,url
        except Exception as e:
            print(f"  attempt {attempt}/3: {e}")
            if attempt<3: time.sleep(12*attempt)
    return None,None

def add_watermark(img_path,token_id,rarity,title):
    if not PIL_OK: return img_path
    img=Image.open(img_path).convert("RGB")
    draw=ImageDraw.Draw(img)
    w,h=img.size
    if rarity=="Impossible Diamond":
        draw.text((28,h-72),"Thomas Lee Harvey",fill=(255,255,255))
        draw.text((28,h-48),f"{title} - #{token_id} - 1 of 1",fill=(220,225,235))
    elif rarity=="Black Diamond":
        draw.text((28,h-72),"Thomas Lee Harvey",fill=(225,230,240))
        draw.text((28,h-48),f"{title} - #{token_id}",fill=(185,195,210))
    else:
        draw.text((28,h-48),f"{title} - #{token_id}",fill=(160,170,185))
    img.save(img_path,optimize=True,quality=99)
    return img_path

def om109_sign(token_id,image_hash):
    genesis=hashlib.sha256(GENESIS_SEED.encode()).hexdigest()
    sig_a=hashlib.sha256(f"{genesis}:A:{token_id}:{image_hash}".encode()).hexdigest()
    sig_b=hashlib.sha256(f"{genesis}:B:{token_id}:{image_hash}:{sig_a}".encode()).hexdigest()
    fp=hashlib.sha256(f"{sig_a[:32]}{sig_b[:32]}".encode()).hexdigest()
    return {"sig_a":sig_a,"sig_b":sig_b,"om109_fingerprint":fp}

def ledger_mint_jsonl(token_id,image_hash,om109,rarity,structure_desc,title,ts):
    global _LAST_CHAIN_HASH
    if LEDGER_LOG.exists():
        lines=[l for l in LEDGER_LOG.read_text().splitlines() if l.strip()]
        if lines: _LAST_CHAIN_HASH=json.loads(lines[-1]).get("chain_hash",_LAST_CHAIN_HASH)
    entry={"event_type":"NFT_MINT","token_id":token_id,"collection":COLLECTION,"creator":CREATOR,
           "title":title,"image_sha256":image_hash,"rarity":rarity,"theme":structure_desc,
           "om109_fingerprint":om109["om109_fingerprint"],"sig_a":om109["sig_a"],"sig_b":om109["sig_b"],
           "minted_at":ts,"prev_chain_hash":_LAST_CHAIN_HASH}
    entry["chain_hash"]=hashlib.sha256(json.dumps(entry,sort_keys=True).encode()).hexdigest()
    _LAST_CHAIN_HASH=entry["chain_hash"]
    with open(LEDGER_LOG,"a") as f: f.write(json.dumps(entry)+"\n")
    return entry["chain_hash"]

def ledger_mint_psql(token_id,image_hash,om109,rarity,title,chain_hash):
    try:
        import psycopg2
        conn=psycopg2.connect(host="127.0.0.1",port=5432,dbname="omega_bank",user="postgres",connect_timeout=5)
        conn.autocommit=True
        cur=conn.cursor()
        idem=hashlib.sha256(f"PARACOSM_MINT:{token_id}:{image_hash}".encode()).hexdigest()[:32]
        cur.execute("INSERT INTO ledger_entries (transaction_id,wallet_id,event_type,amount,direction,debit_account,credit_account,memo,idempotency_key,om109_fingerprint,chain_hash) VALUES (uuid_generate_v4(),'2db2e016-f6a1-4086-bec2-363edfb1c26b',%s,0.01,'CREDIT','paracosm_collection','omega_treasury',%s,%s,%s,%s) ON CONFLICT(idempotency_key) DO NOTHING",
            (f"PARACOSM_MINT_{rarity.upper().replace(' ','_')}",f"PARACOSM #{token_id} '{title}' {rarity}",idem,om109["om109_fingerprint"],chain_hash))
        conn.close()
        print(f"  ledger PSQL: recorded #{token_id}")
    except Exception as e:
        print(f"  ledger PSQL offline: {e}")

def ledger_mint_registry(token_id,title,rarity,structure_desc,image_hash,om109,chain_hash):
    try:
        import psycopg2
        conn=psycopg2.connect(host="127.0.0.1",port=5432,dbname="omega_ledger",user="postgres",connect_timeout=5)
        conn.autocommit=True
        cur=conn.cursor()
        cur.execute("INSERT INTO nft_registry (token_id,name,title,rarity,theme,image_sha256,om109_fingerprint,om109_sig_a,om109_sig_b,chain_hash,owner_account_id,collection) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (collection,token_id) DO NOTHING",
            (token_id,f"Paracosm - {title} #{token_id}",title,rarity,structure_desc,image_hash,om109["om109_fingerprint"],om109["sig_a"],om109["sig_b"],chain_hash,"UNASSIGNED",COLLECTION))
        conn.close()
        print(f"  registry: recorded #{token_id}")
    except Exception as e:
        print(f"  registry offline: {e}")

def build_metadata(token_id,rarity,title,structure_desc,physics_desc,color_desc,image_hash,om109_fp,chain_hash,poll_url):
    is_signed=rarity in ("Impossible Diamond","Black Diamond")
    palette=["Architectural Grey","Impossible Stone","Gravity Defiant","Escher Chrome","Liminal Concrete"][token_id%5]
    return {"name":f"Paracosm - Unique #{token_id}" if rarity=="Impossible Diamond" else f"Paracosm - {title} #{token_id}",
        "description":f"\"{title}\" is a 1-of-100 hyper-surrealist NFT from Paracosm by Thomas Lee Harvey. {structure_desc}. {physics_desc}. OM109 authenticated. Rarity: {rarity}.",
        "image":poll_url,"image_local":f"images/{token_id}.png","collection":COLLECTION,"creator":CREATOR,
        "rarity":rarity,"title":"Unique" if rarity=="Impossible Diamond" else title,"token_id":token_id,
        "total_supply":TOTAL_SUPPLY,"image_sha256":image_hash,"om109_fingerprint":om109_fp,"om109_chain_hash":chain_hash,
        "authentication":"OM109 Alternating Dual-Key Signature",
        "attributes":[{"trait_type":"Rarity","value":rarity},{"trait_type":"Title","value":"Unique" if rarity=="Impossible Diamond" else title},
            {"trait_type":"Edition","value":f"#{token_id} of {TOTAL_SUPPLY}"},{"trait_type":"Creator","value":CREATOR},
            {"trait_type":"Collection","value":COLLECTION},{"trait_type":"Style","value":"Hyper-Surrealist Impossible Architecture"},
            {"trait_type":"Structure","value":structure_desc[:80]},{"trait_type":"Physics Violation","value":physics_desc[:80]},
            {"trait_type":"Accent Color","value":color_desc},{"trait_type":"Palette","value":palette},
            {"trait_type":"Authentication","value":"OM109 Dual-Signature"},{"trait_type":"Signed by Artist","value":"Yes" if is_signed else "No"},
            {"trait_type":"Impossible Diamond","value":"Yes" if rarity=="Impossible Diamond" else "No"}]}

def write_status(minted,total,current_token,current_title,current_rarity,errors):
    STATUS_FILE.write_text(json.dumps({"collection":COLLECTION,"minted":minted,"total":total,"current_token":current_token,
        "current_title":current_title,"current_rarity":current_rarity,"errors":errors,
        "updated_at":datetime.now(timezone.utc).isoformat(),"impossible_tokens":IMPOSSIBLE_TOKENS},indent=2))

def mint_token(token_id):
    rarity,complexity=get_rarity(token_id)
    title=get_title(token_id)
    ts=datetime.now(timezone.utc).isoformat()
    prompt,negative,concept=build_prompt(token_id,complexity)
    structure_desc,physics_desc,color_desc=concept
    print(f"\n{'='*55}\n  #{token_id} '{title}' [{rarity}]\n  Structure: {structure_desc[:60]}\n  Color: {color_desc}\n{'='*55}")
    img_path,poll_url=generate_image(token_id,prompt,negative,complexity)
    if not img_path:
        print(f"  ERROR: generation failed for #{token_id}")
        return False
    add_watermark(img_path,token_id,rarity,title)
    push_to_gallery(img_path,token_id)
    image_hash=hashlib.sha256(img_path.read_bytes()).hexdigest()
    om109=om109_sign(token_id,image_hash)
    chain_hash=ledger_mint_jsonl(token_id,image_hash,om109,rarity,structure_desc,title,ts)
    ledger_mint_psql(token_id,image_hash,om109,rarity,title,chain_hash)
    ledger_mint_registry(token_id,title,rarity,structure_desc,image_hash,om109,chain_hash)
    meta=build_metadata(token_id,rarity,title,structure_desc,physics_desc,color_desc,image_hash,om109["om109_fingerprint"],chain_hash,poll_url)
    with open(META_DIR/f"{token_id}.json","w") as f: json.dump(meta,f,indent=2)
    print(f"  MINTED: {title} #{token_id} - {rarity}")
    return True

def verify_ledger():
    if not LEDGER_LOG.exists(): print("No ledger."); return
    entries=[json.loads(l) for l in LEDGER_LOG.read_text().splitlines() if l.strip()]
    prev="PARACOSM_GENESIS"; ok=0
    for e in entries:
        check=dict(e); stored=check.pop("chain_hash")
        expected=hashlib.sha256(json.dumps(check,sort_keys=True).encode()).hexdigest()
        if expected!=stored or e.get("prev_chain_hash")!=prev:
            print(f"CHAIN BREAK at #{e['token_id']}"); return
        prev=stored; ok+=1
    print(f"ALL CLEAN - {ok} entries verified")

def main():
    if "--verify" in sys.argv: verify_ledger(); return
    print(f"\nPARACOSM - Thomas Lee Harvey\nImpossible Diamonds: {IMPOSSIBLE_TOKENS}\n")
    minted,errors=0,[]
    existing={int(f.stem) for f in IMAGES_DIR.glob("*.png")}
    for token_id in range(TOKEN_OFFSET+1,TOKEN_OFFSET+TOTAL_SUPPLY+1):
        if token_id in existing:
            minted+=1; continue
        rarity,_=get_rarity(token_id); title=get_title(token_id)
        write_status(minted,TOTAL_SUPPLY,token_id,title,rarity,errors)
        ok=mint_token(token_id)
        if ok: minted+=1
        else: errors.append(token_id)
        write_status(minted,TOTAL_SUPPLY,token_id,title,rarity,errors)
        time.sleep(2)
    print(f"\nPARACOSM COMPLETE: {minted}/{TOTAL_SUPPLY} minted")
    if errors: print(f"Failed: {errors}")

if __name__=="__main__":
    main()
