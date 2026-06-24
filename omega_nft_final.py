#!/usr/bin/env python3
"""
ECHOES OF ETERNITY — NFT Engine v2.0
Thomas Lee Harvey · Omega AI · OM109 Authenticated
"""
import os,sys,json,time,random,hashlib,argparse,psycopg2
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

WIDTH=1024
HEIGHT=1024
OMEGA_GENESIS_SEED="OMEGA_GENESIS_THOMAS_LEE_HARVEY_OM109_2024"
_LAST_CHAIN_HASH="OMEGA_NFT_GENESIS"

SURREAL_TITLES=["Dissolution","Phantom","Reverie","Absence","Liminal","Specter","Umbra","Chrysalis","Vestige","Epoch","Mirage","Cipher","Elegy","Fracture","Nocturne","Abyss","Threshold","Remnant","Void","Seance","Penumbra","Entropy","Wraith","Fugue","Chimera","Lacuna","Omen","Solstice","Relic","Paradox","Eclipse","Amnesia","Veil","Requiem","Stasis","Hollow","Meridian","Drift","Cascade","Sigil","Flux","Mythos","Animus","Crypt","Dusk","Zenith","Lament","Obsidian","Resonance","Effigy","Wither","Limbo","Revenant","Chasm","Gossamer"]

PERSPECTIVES=["extreme close-up macro shot, subject fills 80% of frame","low angle shot, camera at ground level looking up dramatically","overhead bird's eye view, subject centered from directly above","three-quarter angle, subject slightly left of center","wide establishing shot, subject small against vast environment","dutch angle tilted 15 degrees, unsettling perspective","eye level centered, classical still life composition","close-up with shallow depth of field, background completely dissolved"]

PHANTOM_SHADOWS=[("a cathedral that isn't there","a single orchid covered in mercury droplets","iridescent violet"),("an hourglass filled with smoke","a glass pomegranate weeping crystalline tears","deep crimson"),("a lighthouse on an impossible shore","a cracked porcelain hand holding still water","electric teal"),("a grand piano melting into the floor","a golden key dripping liquid amber","liquid gold"),("a throne of bones","a white rose wrapped in barbed wire","bone white and rust"),("a giant eyeball on a pedestal","a moth with wings made of stained glass","amber and obsidian"),("a clock tower dissolving into birds","a compass with no needle floating mid-air","verdigris copper"),("a ship sailing through solid ground","a glass bottle containing a tiny storm","storm grey and lightning blue"),("a figure made entirely of smoke","a single match burning upward in zero gravity","ember orange"),("a skyscraper made of ice","a crow holding a small planet in its beak","glacial blue"),("a tree growing downward from the sky","a mechanical heart still beating","arterial red"),("an absent dancer mid-leap","a ballet shoe filled with black sand","pale gold"),("a whale floating above the scene","a compass rose carved into a human tooth","deep ocean teal"),("a library with no walls","a book with pages made of frozen fire","ink black and flame"),("a mountain turned upside down","a snow globe containing a burning city","ash white"),("a giant hand reaching from the floor","a pocket watch with a mirror face","antique brass"),("a wolf made of shadow","a lantern containing a living firefly galaxy","bioluminescent green"),("a second moon just out of frame","a crescent-shaped shard of moonstone","lunar silver"),("a doorway to nowhere","a key made of frozen light","void black and white"),("a crown floating above empty space","a single playing card dissolving into moths","royal purple"),("a jellyfish the size of a building","a tiny ship in a bottle navigating its tendrils","deep sea bioluminescent"),("a spiral staircase with no structure","an hourglass where sand flows upward","marble and gold"),("a telephone ringing in an empty field","a rotary dial phone wrapped in vines","verdant green"),("a mirror reflecting a different world","a hand reaching through cracked glass","mercury silver"),("a river flowing upward on the wall","a fish skeleton made of crystal","sapphire blue"),("an absent chess player mid-move","a single chess piece made of black obsidian","alabaster and jet"),("a volcano made of ice","a flame that casts a shadow of water","glacial fire"),("a city seen from underwater","a submarine periscope emerging from dry land","submarine green"),("a funeral for the sun","a single black candle burning upward light","mourning violet"),("a typewriter writing on its own","a letter sealed with wax dripping upward","ink and rust")]

ENVIRONMENTS=["on a concrete surface, dramatic studio lighting from the left","on polished obsidian, single overhead spotlight","on weathered marble, soft diffused gallery light","on cracked desert earth, harsh noon sun from above","on wet stone, cold blue moonlight","on aged wood, warm amber candlelight from the right","on frosted glass surface, backlit with cold white light","on matte black surface, twin spotlights creating double shadows","on brushed steel, fluorescent clinical lighting","on ancient parchment texture, golden hour side light"]

DROPLET_STYLES=["covered in photorealistic water droplets with light refraction","beaded with mercury-like spherical droplets","dripping with crystalline dew, each drop a perfect lens","coated in condensation, micro-droplets catching the light","wrapped in a thin film of water with large rolling drops"]

TOTAL_SUPPLY=100
_rng=random.Random("OMEGA_GENESIS_THOMAS_LEE_HARVEY_OM109_2024_IMPOSSIBLE")
IMPOSSIBLE_DIAMOND_TOKEN=_rng.randint(1,TOTAL_SUPPLY)

def get_rarity(token_id):
    if token_id==IMPOSSIBLE_DIAMOND_TOKEN: return "Impossible Diamond",6
    random.seed(token_id*9999)
    r=random.random()
    if r<0.005: return "Black Diamond",5
    elif r<0.015: return "Super Rare",4
    elif r<0.165: return "Rare",3
    elif r<0.465: return "Medium",2
    else: return "Common",1

def get_title(token_id):
    if token_id==1: return "Unique"
    random.seed(token_id*3137)
    return SURREAL_TITLES[int(random.random()*len(SURREAL_TITLES))]

def build_prompt(token_id,complexity):
    random.seed(token_id*7331+complexity)
    concept=PHANTOM_SHADOWS[token_id%len(PHANTOM_SHADOWS)]
    env=ENVIRONMENTS[token_id%len(ENVIRONMENTS)]
    droplets=DROPLET_STYLES[token_id%len(DROPLET_STYLES)]
    perspective=PERSPECTIVES[token_id%len(PERSPECTIVES)]
    shadow_desc,subject_desc,color_desc=concept
    prompt=(f"Fine art surrealist studio photography, hyperrealistic, 12k resolution, {perspective}. Full frame composition filling the entire image edge to edge, no black borders. Soft silver-grey background, clean studio environment, {env}. Large dramatic shadow of {shadow_desc} cast sharply across the background wall, the object casting the shadow is completely absent from the scene. Centered in the foreground: {subject_desc}, {droplets}, vivid saturated {color_desc} — the only color in the entire monochrome scene. Medium format photography, tack sharp subject, soft dissolved background, Gregory Crewdson and Magritte surrealist aesthetic, collector fine art NFT, museum quality print, no text, no watermark.")
    negative="cartoon,anime,painting,illustration,low quality,blurry,colorful background,text,watermark,border,ugly,deformed,black bars,letterbox,padding"
    return prompt,negative,concept

def generate_image(token_id,prompt,negative,complexity):
    out_path=IMAGES_DIR/f"{token_id:04d}.png"
    if out_path.exists():
        print(f"  image {token_id:04d} exists, skipping")
        return out_path
    steps={1:30,2:35,3:40,4:45,5:55,6:65}[complexity]
    seed=token_id*137+complexity
    url=(f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=768&height=1024&seed={seed}&steps={steps}&negative={quote(negative)}&model=flux&nologo=true&enhance=true")
    print(f"  generating #{token_id:04d} ({steps} steps)...")
    for attempt in range(1,4):
        try:
            with urlopen(Request(url,headers={"User-Agent":"OmegaNFT/2.0"}),timeout=150) as r:
                data=r.read()
            with open(out_path,"wb") as f: f.write(data)
            print(f"  saved {out_path.name} ({len(data)//1024}KB)")
            return out_path
        except Exception as e:
            print(f"  attempt {attempt}/3: {e}")
            if attempt<3: time.sleep(12*attempt)
    return None

def autocrop_black_bars(img):
    """Remove black letterbox bars top and bottom."""
    import numpy as np
    arr = np.array(img.convert("L"))
    # Find rows that are not mostly black (threshold > 15)
    row_max = arr.max(axis=1)
    non_black = np.where(row_max > 15)[0]
    if len(non_black) == 0:
        return img
    top, bottom = non_black[0], non_black[-1]
    # Only crop if bars are significant (>3% of height)
    if top > img.height * 0.03 or bottom < img.height * 0.97:
        img = img.crop((0, top, img.width, bottom+1))
    return img

def post_process(img_path,complexity):
    if not PIL_OK: return img_path
    img=Image.open(img_path).convert("RGB")
    # Auto-crop black bars first
    try:
        import numpy as np
        img = autocrop_black_bars(img)
    except ImportError:
        pass
    img=ImageEnhance.Contrast(img).enhance(1.3+complexity*0.05)
    img=ImageEnhance.Brightness(img).enhance(1.05)
    img=ImageEnhance.Color(img).enhance(2.0+complexity*0.12)
    img=img.filter(ImageFilter.SHARPEN)
    img=img.filter(ImageFilter.SHARPEN)
    img.save(img_path,optimize=True,quality=99)
    return img_path

def add_watermark(img_path,token_id,rarity,title):
    if not PIL_OK: return img_path
    img=Image.open(img_path).convert("RGB")
    draw=ImageDraw.Draw(img)
    w,h=img.size
    # Seed number top left — very dim, barely visible
    seed_num = token_id * 137
    draw.text((18,16),f"s{seed_num}",fill=(90,90,90))
    # Signed pieces only — bottom RIGHT, very dim
    if rarity in ("Impossible Diamond","Black Diamond"):
        if rarity=="Impossible Diamond":
            line1="Thomas Lee Harvey"
            line2=f"{title}  ·  #{token_id:04d}  ·  1 of 1"
        else:
            line1="Thomas Lee Harvey"
            line2=f"{title}  ·  #{token_id:04d}"
        # Measure text width to right-align
        line1_w = len(line1)*6
        line2_w = len(line2)*6
        draw.text((w-line1_w-24,h-68),line1,fill=(110,115,120))
        draw.text((w-line2_w-24,h-44),line2,fill=(90,95,100))
    img.save(img_path,optimize=True,quality=99)
    return img_path

def hash_image(img_path):
    with open(img_path,"rb") as f: return hashlib.sha256(f.read()).hexdigest()

def om109_sign(token_id,image_hash):
    genesis=hashlib.sha256(OMEGA_GENESIS_SEED.encode()).hexdigest()
    sig_a=hashlib.sha256(f"{genesis}:A:{token_id}:{image_hash}".encode()).hexdigest()
    sig_b=hashlib.sha256(f"{genesis}:B:{token_id}:{image_hash}:{sig_a}".encode()).hexdigest()
    fp=hashlib.sha256(f"{sig_a[:32]}{sig_b[:32]}".encode()).hexdigest()
    return {"sig_a":sig_a,"sig_b":sig_b,"om109_fingerprint":fp}

def ledger_mint_jsonl(token_id,image_hash,om109,rarity,theme,title,ts):
    global _LAST_CHAIN_HASH
    if LEDGER_LOG.exists():
        lines=[l.strip() for l in open(LEDGER_LOG) if l.strip()]
        if lines: _LAST_CHAIN_HASH=json.loads(lines[-1]).get("chain_hash",_LAST_CHAIN_HASH)
    entry={"event_type":"NFT_MINT","token_id":token_id,"collection":"Echoes of Eternity","creator":"Thomas Lee Harvey","title":title,"image_sha256":image_hash,"rarity":rarity,"theme":theme,"om109_fingerprint":om109["om109_fingerprint"],"sig_a":om109["sig_a"],"sig_b":om109["sig_b"],"minted_at":ts,"prev_chain_hash":_LAST_CHAIN_HASH}
    entry["chain_hash"]=hashlib.sha256(json.dumps(entry,sort_keys=True).encode()).hexdigest()
    _LAST_CHAIN_HASH=entry["chain_hash"]
    with open(LEDGER_LOG,"a") as f: f.write(json.dumps(entry)+"\n")
    return entry["chain_hash"]

def ledger_mint_psql(token_id,image_hash,om109,rarity,title,chain_hash):
    try:
        conn=psycopg2.connect(host="127.0.0.1",port=5432,dbname="omega_bank",user="postgres",connect_timeout=5)
        conn.autocommit=True
        cur=conn.cursor()
        idem=hashlib.sha256(f"NFT_MINT:{token_id}:{image_hash}".encode()).hexdigest()[:32]
        cur.execute("INSERT INTO ledger_entries (transaction_id,wallet_id,event_type,amount,direction,debit_account,credit_account,memo,idempotency_key,om109_fingerprint,chain_hash) VALUES (uuid_generate_v4(),'2db2e016-f6a1-4086-bec2-363edfb1c26b',%s,0.00,'CREDIT','nft_collection','omega_treasury',%s,%s,%s,%s) ON CONFLICT(idempotency_key) DO NOTHING",
            (f"NFT_MINT_{rarity.upper().replace(' ','_')}",f"NFT #{token_id:04d} '{title}' {rarity} | SHA256:{image_hash[:16]}",idem,om109["om109_fingerprint"],chain_hash))
        conn.close()
        print(f"  ledger PSQL: recorded #{token_id:04d} on omega_bank")
    except Exception as e:
        print(f"  ledger PSQL: offline ({e}) — JSONL only")

def build_metadata(token_id,rarity,title,shadow_desc,subject_desc,color_desc,image_hash,om109_fp,chain_hash):
    from datetime import datetime,timezone
    palette=["Abyss Monochrome","Dreamfire Void","BioLume Dark","VoidBloom","GoldenVoid"][token_id%5]
    minted_at=datetime.now(timezone.utc).isoformat()
    is_signed = rarity in ("Impossible Diamond","Black Diamond")
    return {
        "name": f"Echoes of Eternity — {title} #{token_id:04d}" if rarity!="Impossible Diamond" else f"Echoes of Eternity — Unique #{token_id:04d}",
        "description": (
            f"\"{title}\" is a 1-of-100 surrealist fine art NFT from the Echoes of Eternity collection "
            f"by Thomas Lee Harvey. "
            f"The shadow of {shadow_desc} dominates a monochrome grey world, "
            f"cast by something entirely absent from the scene. "
            f"The only color in the photograph belongs to {subject_desc}. "
            f"Every token is authenticated by OM109 alternating dual-key signature — "
            f"the same cryptographic primitive securing the Omega Bank distributed ledger. "
            f"Rarity: {rarity}. Edition {token_id} of {TOTAL_SUPPLY}."
        ),
        "image": f"ipfs://YOUR_CID/images/{token_id:04d}.png",
        "external_url": "https://omegaops.ai",
        "edition": token_id,
        "total_supply": TOTAL_SUPPLY,
        "rarity": rarity,
        "title": "Unique" if rarity=="Impossible Diamond" else title,
        "creator": "Thomas Lee Harvey",
        "collection": "Echoes of Eternity",
        "minted_at": minted_at,
        "image_sha256": image_hash,
        "om109_fingerprint": om109_fp,
        "om109_chain_hash": chain_hash,
        "authentication": "OM109 Alternating Dual-Key Signature",
        "attributes": [
            {"trait_type":"Rarity","value":rarity},
            {"trait_type":"Title","value":"Unique" if rarity=="Impossible Diamond" else title},
            {"trait_type":"Edition","value":f"{token_id} of {TOTAL_SUPPLY}"},
            {"trait_type":"Creator","value":"Thomas Lee Harvey"},
            {"trait_type":"Collection","value":"Echoes of Eternity"},
            {"trait_type":"Style","value":"Hyper-Surrealist Fine Art Photography"},
            {"trait_type":"Phantom Shadow","value":shadow_desc},
            {"trait_type":"Color Subject","value":subject_desc[:60]},
            {"trait_type":"Accent Color","value":color_desc},
            {"trait_type":"Color Palette","value":palette},
            {"trait_type":"Authentication","value":"OM109 Dual-Signature"},
            {"trait_type":"SHA256 Fingerprint","value":image_hash},
            {"trait_type":"Signed by Artist","value":"Yes" if is_signed else "No"},
            {"trait_type":"Format","value":"1024x1024 PNG"},
            {"trait_type":"Year","value":"2026"},
        ]
    }

def mint_token(token_id):
    print(f"\n{'='*54}\n  MINTING  #{token_id:04d}\n{'='*54}")
    rarity,complexity=get_rarity(token_id)
    title=get_title(token_id)
    prompt,negative,concept=build_prompt(token_id,complexity)
    shadow_desc,subject_desc,color_desc=concept
    print(f"  Title   : {title}\n  Rarity  : {rarity}\n  Shadow  : {shadow_desc}\n  Color   : {color_desc}")
    img_path=generate_image(token_id,prompt,negative,complexity)
    if not img_path: return False
    post_process(img_path,complexity)
    add_watermark(img_path,token_id,rarity,title)
    image_hash=hash_image(img_path)
    om109=om109_sign(token_id,image_hash)
    ts=datetime.now(timezone.utc).isoformat()
    chain_hash=ledger_mint_jsonl(token_id,image_hash,om109,rarity,shadow_desc,title,ts)
    ledger_mint_psql(token_id,image_hash,om109,rarity,title,chain_hash)
    meta=build_metadata(token_id,rarity,title,shadow_desc,subject_desc,color_desc,image_hash,om109["om109_fingerprint"],chain_hash)
    with open(META_DIR/f"{token_id:04d}.json","w") as f: json.dump(meta,f,indent=2)
    print(f"  OM109   : {om109['om109_fingerprint'][:32]}...\n  Chain   : {chain_hash[:32]}...\n  MINTED  : {title} #{token_id:04d} - {rarity}")
    return True

def verify_ledger():
    if not LEDGER_LOG.exists(): print("No ledger found."); return
    entries=[json.loads(l) for l in open(LEDGER_LOG) if l.strip()]
    print(f"\nVerifying {len(entries)} ledger entries...")
    errors=0; prev="OMEGA_NFT_GENESIS"
    for e in entries:
        if e.get("prev_chain_hash")!=prev: print(f"  CHAIN BREAK #{e['token_id']}"); errors+=1
        prev=e.get("chain_hash","")
    print(f"  {'ALL CLEAN' if not errors else str(errors)+' ERRORS'} - {len(entries)} entries")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--count",type=int,default=3)
    parser.add_argument("--id",type=int,default=None)
    parser.add_argument("--start",type=int,default=1)
    parser.add_argument("--verify",action="store_true")
    args=parser.parse_args()
    print("\n ECHOES OF ETERNITY v2.0 - Thomas Lee Harvey - Omega AI")
    print(f" Output: {BASE}\n")
    if args.verify: verify_ledger(); return
    if args.id: mint_token(args.id); return
    existing={int(f.stem) for f in IMAGES_DIR.glob("*.png")}
    success=0; t0=time.time()
    for i in range(args.start,args.start+args.count):
        if i in existing: print(f"  skip #{i:04d} - already minted"); success+=1; continue
        if mint_token(i): success+=1
        if i<args.start+args.count-1: time.sleep(3)
    print(f"\n COMPLETE: {success}/{args.count} | {time.time()-t0:.0f}s\n Images: {IMAGES_DIR}\n Ledger: {LEDGER_LOG}\n")

if __name__=="__main__":
    main()
