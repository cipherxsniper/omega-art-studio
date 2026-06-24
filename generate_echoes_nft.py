import os
import random
import json
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

OUTPUT_DIR = "/sdcard/Pictures/Echoes_of_Eternity"
os.makedirs(OUTPUT_DIR + "/images", exist_ok=True)
os.makedirs(OUTPUT_DIR + "/metadata", exist_ok=True)

TOTAL_NFTS = 1000
WIDTH, HEIGHT = 1024, 1024

def get_rarity_tier(token_id):
    r = random.random()
    if token_id <= 2 or r < 0.002:   # Black Diamond - only 2
        return "Black Diamond", 5
    elif r < 0.012:                 # Super Rare ~10
        return "Super Rare", 4
    elif r < 0.162:                 # Rare
        return "Rare", 3
    elif r < 0.462:                 # Medium
        return "Medium", 2
    else:
        return "Common", 1

def create_surreal_image(token_id):
    rarity_name, complexity = get_rarity_tier(token_id)
    random.seed(token_id + complexity * 1000)  # Deterministic yet rarity-influenced
    
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(8, 8, 25))  # Deep cosmic base
    draw = ImageDraw.Draw(img)
    
    # === BACKGROUND: Black/White with bold impossible colors ===
    for _ in range(25 * complexity):
        x1 = random.randint(0, WIDTH)
        y1 = random.randint(0, HEIGHT)
        x2 = x1 + random.randint(-400, 400)
        y2 = y1 + random.randint(-400, 400)
        color = random.choice([(255, 50, 150), (0, 255, 220), (255, 215, 0), (180, 0, 255)])
        draw.line((x1, y1, x2, y2), fill=color, width=random.randint(3, 18))
    
    # === LIQUID MATHEMATICS & IMPOSSIBLE GEOMETRY ===
    for _ in range(12 * complexity):
        cx = random.randint(100, WIDTH-100)
        cy = random.randint(100, HEIGHT-100)
        r = random.randint(40, 180)
        draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=(255, 255, 255), width=6)
        # Impossible overlapping
        draw.polygon([ (cx-random.randint(50,120), cy), (cx, cy-random.randint(80,150)), 
                      (cx+random.randint(50,120), cy) ], fill=None, outline=(0, 255, 200))
    
    # === REGENERATIVE JELLYFISH ORGANIC FORMS ===
    for _ in range(5 + complexity):
        cx, cy = random.randint(150, WIDTH-150), random.randint(120, HEIGHT-150)
        r = random.randint(90, 260)
        for i in range(r, 30, -25):
            alpha_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
            a_draw = ImageDraw.Draw(alpha_layer)
            a_draw.ellipse((cx-i, cy-i, cx+i, cy+i), 
                          fill=(random.randint(100,180), 255, random.randint(180,255), 70))
            img = Image.alpha_composite(img.convert("RGBA"), alpha_layer)
    
    # === CRISP TEAL APPLE + HYPER-DETAILED DROPLETS + SHADOWS ===
    apple_cx = random.randint(350, 680)
    apple_cy = random.randint(380, 680)
    apple_r = 145
    # Teal apple with surreal gradient
    for i in range(apple_r, 0, -4):
        b = int(70 + (i/apple_r)*160)
        draw.ellipse((apple_cx-i, apple_cy-i, apple_cx+i, apple_cy+i), fill=(0, b+30, b-20))
    
    # Super sharp water droplets
    for _ in range(28 + complexity*8):
        dx = random.randint(-115, 115)
        dy = random.randint(-115, 90)
        dr = random.randint(5, 18)
        draw.ellipse((apple_cx+dx-dr, apple_cy+dy-dr, apple_cx+dx+dr, apple_cy+dy+dr),
                    fill=(220, 255, 255), outline=(255,255,255), width=3)
    
    # Cast shadow with emerging forms
    shadow_y = apple_cy + 145
    draw.ellipse((apple_cx-125, shadow_y, apple_cx+125, shadow_y+55), fill=(0,0,0,140))
    # Things emerging from shadow
    if complexity > 2:
        for _ in range(3):
            draw.line((apple_cx-80, shadow_y+20, apple_cx-random.randint(-60,100), shadow_y-random.randint(80,160)),
                     fill=(0, 255, 180), width=12)
    
    # === VASE SHADOW + HANGING LEAVES (odd angles) ===
    vx, vy = apple_cx - 210, apple_cy - 260
    draw.polygon([(vx-45, vy+190), (vx+45, vy+190), (vx+30, vy+70), (vx-30, vy+70)], fill=(35, 25, 55))
    for _ in range(14 + complexity):
        lx = vx + random.randint(-70, 110)
        ly = vy + random.randint(-160, 40)
        draw.line((vx, vy-40, lx, ly), fill=(40, 180, 90), width=random.randint(14, 26))
    
    # === FINAL ENHANCEMENTS (rarer = sharper & more contrast) ===
    img = img.filter(ImageFilter.SHARPEN)
    if complexity > 3:
        img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.4 + complexity*0.2)
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.15)
    
    # Signature
    draw.text((60, HEIGHT - 65), "Thomas Lee Harvey", fill=(220, 240, 255), font=None)
    
    return img, rarity_name

print("🚀 Starting 1000 Echoes of Eternity: Jellyfish Dreams generation...")
for i in range(1, TOTAL_NFTS + 1):
    img, rarity = create_surreal_image(i)
    filename = f"{i:04d}"
    
    img.save(f"{OUTPUT_DIR}/images/{filename}.png", quality=95)
    
    metadata = {
        "name": f"Echoes of Eternity: Jellyfish Dreams #{i}",
        "description": f"Surreal Abstract Realism NFT by Thomas Lee Harvey. {rarity} tier. Inspired by Immortal Jellyfish Hypothesis, regenerative consciousness, liquid mathematics, and OM109 systems.",
        "image": f"ipfs://YOUR_CID/images/{filename}.png",
        "edition": i,
        "rarity": rarity,
        "attributes": [
            {"trait_type": "Rarity", "value": rarity},
            {"trait_type": "Creator", "value": "Thomas Lee Harvey"},
            {"trait_type": "Style", "value": "Surreal Abstract Realism"},
            {"trait_type": "Theme", "value": random.choice(["Transdifferentiation", "Liquid Mathematics", "Cosmic Regeneration", "Impossible Geometry"])}
        ]
    }
    
    with open(f"{OUTPUT_DIR}/metadata/{filename}.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    if i % 100 == 0 or rarity in ["Black Diamond", "Super Rare"]:
        print(f"✅ #{i} | {rarity} generated")

print(f"🎉 Generation complete! All files saved to {OUTPUT_DIR}")
print("Open your Photos app → Echoes_of_Eternity folder")
