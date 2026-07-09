#!/usr/bin/env python3
import os,sys,json,time,random,hashlib,argparse
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import urlopen,Request
from urllib.parse import quote
try:
    from PIL import Image,ImageEnhance,ImageFilter,ImageDraw,ImageChops
    PIL_OK=True
except:
    PIL_OK=False

BASE=Path.home()/"echoes_of_eternity"
IMAGES_DIR=BASE/"images"
META_DIR=BASE/"metadata"
CERT_DIR=BASE/"certificates"
LEDGER_LOG=BASE/"om109_ledger.jsonl"
for d in [IMAGES_DIR,META_DIR,CERT_DIR]:
    d.mkdir(parents=True,exist_ok=True)
WIDTH=768
HEIGHT=768
OMEGA_GENESIS_SEED="OMEGA_GENESIS_THOMAS_LEE_HARVEY_OM109_2024"
_LAST_CHAIN_HASH="OMEGA_NFT_GENESIS"

def get_rarity(token_id):
    if token_id==1: return "Impossible Diamond",6
    random.seed(token_id*9999)
    r=random.random()
    if token_id<=6 or r<0.002: return "Black Diamond",5
    elif r<0.012: return "Super Rare",4
    elif r<0.162: return "Rare",3
    elif r<0.462: return "Medium",2
    else: return "Common",1

PHANTOM_SHADOWS=[
    ("a cathedral that isn't there","a single orchid covered in mercury droplets","iridescent violet"),
    ("an hourglass filled with smoke","a glass pomegranate weeping crystalline tears","deep crimson"),
    ("a lighthouse on an impossible shore","a cracked porcelain hand holding still water","electric teal"),
    ("a grand piano melting into the floor","a golden key dripping liquid amber","liquid gold"),
    ("a throne of bones","a white rose wrapped in barbed wire","bone white and rust"),
    ("a giant eyeball on a pedestal","a moth with wings made of stained glass","amber and obsidian"),
    ("a clock tower dissolving into birds","a compass with no needle floating mid-air","verdigris copper"),
    ("a ship sailing through solid ground","a glass bottle containing a tiny storm","storm grey and lightning blue"),
    ("a figure made entirely of smoke","a single match burning upward in zero gravity","ember orange"),
    ("a skyscraper made of ice","a crow holding a small planet in its beak","glacial blue"),
    ("a tree growing downward from the sky","a mechanical heart still beating","arterial red"),
    ("an absent dancer mid-leap","a ballet shoe filled with black sand","pale gold"),
    ("a whale floating above the scene","a compass rose carved into a human tooth","deep ocean teal"),
    ("a library with no walls","a book with pages made of frozen fire","ink black and flame"),
    ("a mountain turned upside down","a snow globe containing a burning city","ash white"),
    ("a giant hand reaching from the floor","a pocket watch with a mirror face","antique brass"),
    ("a wolf made of shadow","a lantern containing a living firefly galaxy","bioluminescent green"),
    ("a second moon just out of frame","a crescent-shaped shard of moonstone","lunar silver"),
    ("a doorway to nowhere","a key made of frozen light","void black and white"),
    ("a crown floating above empty space","a single playing card dissolving into moths","royal purple"),
    ("a jellyfish the size of a building","a tiny ship in a bottle navigating its tendrils","deep sea bioluminescent"),
    ("a spiral staircase with no structure","an hourglass where sand flows upward","marble and gold"),
    ("a telephone ringing in an empty field","a rotary dial phone wrapped in vines","verdant green"),
    ("a mirror reflecting a different world","a hand reaching through cracked glass","mercury silver"),
    ("a river flowing upward on the wall","a fish skeleton made of crystal","sapphire blue"),
    ("an absent chess player mid-move","a single chess piece made of black obsidian","alabaster and jet"),
    ("a volcano made of ice","a flame that casts a shadow of water","glacial fire"),
    ("a city seen from underwater","a submarine periscope emerging from dry land","submarine green"),
    ("a funeral for the sun","a single black candle burning upward light","mourning violet"),
    ("a typewriter writing on its own","a letter sealed with wax dripping upward","ink and rust"),
]
ENVIRONMENTS=["on a concrete surface, dramatic studio lighting from the left","on polished obsidian, single overhead spotlight","on weathered marble, soft diffused gallery light","on cracked desert earth, harsh noon sun from above","on wet stone, cold blue moonlight","on aged wood, warm amber candlelight from the right","on frosted glass surface, backlit with cold white light","on matte black surface, twin spotlights creating double shadows","on brushed steel, fluorescent clinical lighting","on ancient parchment texture, golden hour side light"]
DROPLET_STYLES=["covered in photorealistic water droplets with light refraction","beaded with mercury-like spherical droplets","dripping with crystalline dew, each drop a perfect lens","coated in condensation, micro-droplets catching the light","wrapped in a thin film of water with large rolling drops"]
THEMES=["Transdifferentiation","Liquid Mathematics","Cosmic Regeneration","Impossible Geometry","Neural Bioluminescence","Temporal Dissolution","Void Crystallization","Recursive Consciousness","Phantom Cartography","Entropic Memory","Spectral Architecture","Dissolved Identity"]

def build_prompt(token_id,complexity):
    random.seed(token_id*7331+complexity)
    concept=PHANTOM_SHADOWS[token_id%len(PHANTOM_SHADOWS)]
    env=ENVIRONMENTS[token_id%len(ENVIRONMENTS)]
    droplets=DROPLET_STYLES[token_id%len(DROPLET_STYLES)]
    theme=THEMES[token_id%len(THEMES)]
    shadow_desc,subject_desc,color_desc=concept
    prompt=(
        f"Fine art surrealist studio photography, hyperrealistic, 8k resolution. "
        f"Full frame composition filling the entire image edge to edge. "
        f"Soft silver-grey background, clean studio environment, {env}. "
        f"Large dramatic shadow of {shadow_desc} cast sharply across the background wall, "
        f"the object casting the shadow is completely absent — only its shadow exists. "
        f"Centered in the foreground: {subject_desc}, {droplets}, "
        f"vivid saturated {color_desc} — the only color in the entire monochrome scene. "
        f"Medium format photography, sharp subject, soft background, "
        f"Gregory Crewdson and Magritte surrealist aesthetic, "
        f"collector fine art NFT, museum quality print."
    )
    negative="cartoon, anime, painting, illustration, low quality, blurry, multiple colors in background, colorful background, busy, cluttered, text, watermark, signature, frame, border, ugly, deformed"
    return prompt,negative,theme,concept

def generate_image(token_id,prompt,negative,complexity):
    out_path=IMAGES_DIR/f"{token_id:04d}.png"
    if out_path.exists():
        print(f"  image {token_id:04d} exists, skipping")
        return out_path
    steps={1:30,2:35,3:40,4:45,5:50,6:60}[complexity]
    seed=token_id*137+complexity
    encoded=quote(prompt)
    neg_enc=quote(negative)
    url=(f"https://image.pollinations.ai/prompt/{encoded}"
         f"?width={WIDTH}&height={HEIGHT}&seed={seed}&steps={steps}"
         f"&negative={neg_enc}&model=flux&nologo=true")
    print(f"  generating #{token_id:04d} via Pollinations (steps={steps}, seed={seed})...")
    for attempt in range(1,4):
        try:
            req=Request(url,headers={"User-Agent":"OmegaNFT/1.0"})
            with urlopen(req,timeout=120) as resp:
                data=resp.read()
            with open(out_path,"wb") as f:
                f.write(data)
            print(f"  saved {out_path.name} ({len(data)//1024}KB)")
            return out_path
        except Exception as e:
            print(f"  attempt {attempt}/3 failed: {e}")
            if attempt<3:
                time.sleep(10*attempt)
    print(f"  generation failed for #{token_id:04d}")
    return None

def post_process(img_path,complexity):
    if not PIL_OK: return img_path
    img=Image.open(img_path).convert("RGB")
    img=ImageEnhance.Contrast(img).enhance(1.5+complexity*0.08)
    img=ImageEnhance.Brightness(img).enhance(0.93)
    img=ImageEnhance.Color(img).enhance(2.0+complexity*0.12)
    img=img.filter(ImageFilter.SHARPEN)
    img=img.filter(ImageFilter.SHARPEN)
    w,h=img.size
    vignette=Image.new("L",(w,h),0)
    v_draw=ImageDraw.Draw(vignette)
    for i in range(min(w,h)//2,0,-4):
        darkness=int(255*(1-(i/(min(w,h)/2))**1.5))
        v_draw.ellipse([w//2-i,h//2-i,w//2+i,h//2+i],fill=darkness)
    vignette=vignette.filter(ImageFilter.GaussianBlur(40))
    vig_rgb=Image.merge("RGB",[vignette,vignette,vignette])
    img=ImageChops.multiply(img,vig_rgb)
    img=ImageEnhance.Brightness(img).enhance(1.3)
    img.save(img_path,optimize=True,quality=98)
    return img_path

def add_watermark(img_path,token_id,rarity,title="",signed=False):
    if not PIL_OK: return img_path
    img=Image.open(img_path).convert("RGB")
    draw=ImageDraw.Draw(img)
    w,h=img.size
    if signed and rarity=="Impossible Diamond":
        draw.text((28,h-72),f"Thomas Lee Harvey",fill=(255,255,255))
        draw.text((28,h-48),f"{title}  ·  #{token_id:04d}  ·  1 of 1",fill=(220,220,220))
    elif signed:
        draw.text((28,h-72),f"Thomas Lee Harvey",fill=(220,220,220))
        draw.text((28,h-48),f"{title}  ·  #{token_id:04d}",fill=(180,190,200))
    else:
        draw.text((28,h-48),f"{title}  ·  #{token_id:04d}",fill=(160,170,185))
    img.save(img_path,optimize=True,quality=98)
    return img_path

def hash_image(img_path):
    with open(img_path,"rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def om109_sign(token_id,image_hash,rarity):
    genesis=hashlib.sha256(OMEGA_GENESIS_SEED.encode()).hexdigest()
    key_a_raw=f"{genesis}:A:{token_id}:{image_hash}"
    sig_a=hashlib.sha256(key_a_raw.encode()).hexdigest()
    key_b_raw=f"{genesis}:B:{token_id}:{image_hash}:{sig_a}"
    sig_b=hashlib.sha256(key_b_raw.encode()).hexdigest()
    combined=f"{sig_a[:32]}{sig_b[:32]}"
    om109_fp=hashlib.sha256(combined.encode()).hexdigest()
    return {"sig_a":sig_a,"sig_b":sig_b,"om109_fingerprint":om109_fp}

def ledger_mint(token_id,image_hash,om109,rarity,theme,meta):
    global _LAST_CHAIN_HASH
    if LEDGER_LOG.exists():
        with open(LEDGER_LOG,"r") as f:
            lines=[l.strip() for l in f if l.strip()]
        if lines:
            _LAST_CHAIN_HASH=json.loads(lines[-1]).get("chain_hash",_LAST_CHAIN_HASH)
    ts=datetime.now(timezone.utc).isoformat()
    entry={"event_type":"NFT_MINT","token_id":token_id,"collection":"Echoes of Eternity",
           "creator":"Thomas Lee Harvey","image_sha256":image_hash,"rarity":rarity,
           "theme":theme,"om109_fingerprint":om109["om109_fingerprint"],
           "sig_a":om109["sig_a"],"sig_b":om109["sig_b"],
           "minted_at":ts,"prev_chain_hash":_LAST_CHAIN_HASH}
    entry["chain_hash"]=hashlib.sha256(json.dumps(entry,sort_keys=True).encode()).hexdigest()
    _LAST_CHAIN_HASH=entry["chain_hash"]
    with open(LEDGER_LOG,"a") as f:
        f.write(json.dumps(entry)+"\n")
    return entry["chain_hash"],ts

def build_metadata(token_id,rarity,theme,shadow_desc,subject_desc,color_desc,image_hash,om109_fp,chain_hash):
    palette=["Abyss Monochrome","Dreamfire Void","BioLume Dark","VoidBloom","GoldenVoid"][token_id%5]
    return {"name":f"Echoes of Eternity #{token_id:04d}",
            "description":(f"A surrealist NFT by Thomas Lee Harvey. "
                f"The shadow of {shadow_desc} dominates a monochrome world, "
                f"cast by something entirely absent. "
                f"The only color belongs to {subject_desc}. "
                f"Authenticated by OM109 dual-signature."),
            "image":f"ipfs://YOUR_CID/images/{token_id:04d}.png",
            "edition":token_id,"rarity":rarity,
            "image_sha256":image_hash,"om109_fingerprint":om109_fp,"chain_hash":chain_hash,
            "attributes":[
                {"trait_type":"Rarity","value":rarity},
                {"trait_type":"Creator","value":"Thomas Lee Harvey"},
                {"trait_type":"Style","value":"Surreal Abstract Realism"},
                {"trait_type":"Theme","value":theme},
                {"trait_type":"Phantom Shadow","value":shadow_desc},
                {"trait_type":"Color Subject","value":subject_desc[:50]},
                {"trait_type":"Accent Color","value":color_desc},
                {"trait_type":"Palette","value":palette},
                {"trait_type":"Collection","value":"Echoes of Eternity"},
                {"trait_type":"Auth Scheme","value":"OM109 Dual-Signature"},
            ]}

def mint_token(token_id):
    print(f"\n{'='*52}\n  MINTING TOKEN #{token_id:04d}\n{'='*52}")
    rarity,complexity=get_rarity(token_id)
    prompt,negative,theme,concept=build_prompt(token_id,complexity)
    shadow_desc,subject_desc,color_desc=concept
    print(f"  Rarity  : {rarity} (complexity {complexity})")
    print(f"  Theme   : {theme}")
    print(f"  Shadow  : {shadow_desc}")
    print(f"  Subject : {subject_desc[:50]}")
    print(f"  Color   : {color_desc}")
    img_path=generate_image(token_id,prompt,negative,complexity)
    if not img_path:
        print(f"  SKIP #{token_id:04d} — image failed")
        return False
    post_process(img_path,complexity)
    add_watermark(img_path,token_id,rarity,title=get_title(token_id,shadow_desc,subject_desc,color_desc),signed=(rarity in ('Black Diamond','Impossible Diamond')))
    image_hash=hash_image(img_path)
    print(f"  SHA-256 : {image_hash[:32]}...")
    om109=om109_sign(token_id,image_hash,rarity)
    print(f"  OM109   : {om109['om109_fingerprint'][:32]}...")
    chain_hash,ts=ledger_mint(token_id,image_hash,om109,rarity,theme,
                              {"shadow":shadow_desc,"subject":subject_desc})
    print(f"  Chain   : {chain_hash[:32]}...")
    meta=build_metadata(token_id,rarity,theme,shadow_desc,subject_desc,
                        color_desc,image_hash,om109["om109_fingerprint"],chain_hash)
    with open(META_DIR/f"{token_id:04d}.json","w") as f:
        json.dump(meta,f,indent=2)
    print(f"  Metadata saved")
    print(f"  MINTED #{token_id:04d} — {rarity}")
    return True

def verify_ledger():
    if not LEDGER_LOG.exists():
        print("No ledger found.")
        return
    with open(LEDGER_LOG,"r") as f:
        entries=[json.loads(l) for l in f if l.strip()]
    print(f"\nVerifying {len(entries)} ledger entries...")
    errors=0
    prev="OMEGA_NFT_GENESIS"
    for e in entries:
        stored=e.pop("chain_hash",None)
        e["chain_hash"]=stored
        if e.get("prev_chain_hash")!=prev:
            print(f"  CHAIN BREAK at token #{e['token_id']}")
            errors+=1
        prev=stored
    if errors==0:
        print(f"  ALL {len(entries)} entries verified — chain intact")
    else:
        print(f"  {errors} chain errors found")

def main():
    parser=argparse.ArgumentParser(description="Echoes of Eternity NFT Engine")
    parser.add_argument("--count",type=int,default=3)
    parser.add_argument("--id",type=int,default=None)
    parser.add_argument("--verify",action="store_true")
    parser.add_argument("--start",type=int,default=1)
    args=parser.parse_args()
    print("\n ECHOES OF ETERNITY — NFT Engine v1.0")
    print(f" Output: {BASE}\n")
    if args.verify:
        verify_ledger()
        return
    if args.id is not None:
        mint_token(args.id)
        return
    success=0
    start=time.time()
    for i in range(args.start,args.start+args.count):
        ok=mint_token(i)
        if ok: success+=1
        if i<args.start+args.count-1:
            print("  waiting 3s...")
            time.sleep(3)
    elapsed=time.time()-start
    print(f"\n COMPLETE: {success}/{args.count} minted in {elapsed:.0f}s")
    print(f" Images  : {IMAGES_DIR}")
    print(f" Ledger  : {LEDGER_LOG}\n")

if __name__=="__main__":
    main()

# ── PATCH: one-word title engine ─────────────────────────────────
SURREAL_TITLES = [
    "Dissolution","Phantom","Reverie","Absence","Liminal","Specter",
    "Umbra","Chrysalis","Vestige","Epoch","Mirage","Cipher","Elegy",
    "Fracture","Nocturne","Abyss","Threshold","Remnant","Void","Séance",
    "Penumbra","Entropy","Wraith","Fugue","Chimera","Lacuna","Omen",
    "Solstice","Relic","Paradox","Eclipse","Amnesia","Veil","Requiem",
    "Stasis","Hollow","Meridian","Drift","Cascade","Sigil","Flux",
    "Mythos","Animus","Crypt","Dusk","Zenith","Lament","Obsidian",
    "Resonance","Effigy",
]

def get_title(token_id, shadow_desc, subject_desc, color_desc):
    random.seed(token_id * 3137)
    # Weight toward words that match the concept
    combined = (shadow_desc + subject_desc + color_desc).lower()
    scored = []
    for word in SURREAL_TITLES:
        score = random.random()
        scored.append((score, word))
    scored.sort(reverse=True)
    return scored[0][1]
