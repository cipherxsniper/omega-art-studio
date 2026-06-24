with open("/data/data/com.termux/files/home/omega_nft_engine.py","r") as f:
    src=f.read()

# Fix prompt to match teal apple: lighter bg, full frame, centered subject
old_prompt='''    prompt=(
        f"Fine art surrealist photography, medium format film aesthetic, hyperrealistic. "
        f"Complete monochrome world — every surface, wall, object in pure silver-grey desaturated tones, {env}. "
        f"The shadow of {shadow_desc} cast dramatically across the background, "
        f"but its source is entirely absent from the scene — only the shadow remains, "
        f"large, sharp, perfectly defined. "
        f"In the foreground, {subject_desc}, {droplets}, "
        f"rendered in rich saturated {color_desc} — the sole point of color in an otherwise colorless world. "
        f"Photorealistic studio photography, sharp focus, "
        f"soft bokeh background, Magritte and Gregory Crewdson aesthetic, "
        f"collector NFT fine art, masterpiece quality."
    )'''

new_prompt='''    prompt=(
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
    )'''

src=src.replace(old_prompt,new_prompt)

# Fix watermark — 6 signed (Black Diamond + Impossible Diamond), rest title only
old_wm='''def add_watermark(img_path,token_id,rarity,title="",signed=False):
    if not PIL_OK: return img_path
    img=Image.open(img_path).convert("RGB")
    draw=ImageDraw.Draw(img)
    w,h=img.size
    # Bottom left — title + token number always
    if signed:
        draw.text((28,h-52),f"Thomas Lee Harvey  ·  {title}  ·  #{token_id:04d}",fill=(220,220,220))
    else:
        draw.text((28,h-52),f"{title}  ·  #{token_id:04d}",fill=(180,190,200))
    # NO top right watermark
    img.save(img_path,optimize=True,quality=98)
    return img_path'''

new_wm='''def add_watermark(img_path,token_id,rarity,title="",signed=False):
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
    return img_path'''

src=src.replace(old_wm,new_wm)

# Fix get_rarity — add Impossible Diamond for token 1 only
old_rarity='''def get_rarity(token_id):
    random.seed(token_id*9999)
    r=random.random()
    if token_id<=2 or r<0.002: return "Black Diamond",5
    elif r<0.012: return "Super Rare",4
    elif r<0.162: return "Rare",3
    elif r<0.462: return "Medium",2
    else: return "Common",1'''

new_rarity='''def get_rarity(token_id):
    if token_id==1: return "Impossible Diamond",6
    random.seed(token_id*9999)
    r=random.random()
    if token_id<=6 or r<0.002: return "Black Diamond",5
    elif r<0.012: return "Super Rare",4
    elif r<0.162: return "Rare",3
    elif r<0.462: return "Medium",2
    else: return "Common",1'''

src=src.replace(old_rarity,new_rarity)

# Fix signed logic in mint_token call
src=src.replace(
    "signed=(rarity=='Black Diamond')",
    "signed=(rarity in ('Black Diamond','Impossible Diamond'))"
)

# Fix steps dict to handle complexity 6
src=src.replace(
    "steps={1:30,2:35,3:40,4:45,5:50}[complexity]",
    "steps={1:30,2:35,3:40,4:45,5:50,6:60}[complexity]"
)

with open("/data/data/com.termux/files/home/omega_nft_engine.py","w") as f:
    f.write(src)
print("Final patch applied")
