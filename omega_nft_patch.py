import re

with open("/data/data/com.termux/files/home/omega_nft_engine.py", "r") as f:
    src = f.read()

# 1 — Replace add_watermark with new logic
old_wm = '''def add_watermark(img_path,token_id,rarity):
    if not PIL_OK: return img_path
    img=Image.open(img_path).convert("RGB")
    draw=ImageDraw.Draw(img)
    w,h=img.size
    draw.text((28,h-52),f"Thomas Lee Harvey  ##{token_id:04d}  {rarity}",fill=(200,210,220))
    draw.text((w-220,22),"ECHOES OF ETERNITY",fill=(180,190,200))
    img.save(img_path,optimize=True,quality=98)
    return img_path'''

new_wm = '''def add_watermark(img_path,token_id,rarity,title="",signed=False):
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

src = src.replace(old_wm, new_wm)

# 2 — Replace mint_token watermark call
src = src.replace(
    "add_watermark(img_path,token_id,rarity)",
    "add_watermark(img_path,token_id,rarity,title=get_title(token_id,shadow_desc,subject_desc,color_desc),signed=(rarity=='Black Diamond'))"
)

# 3 — Tighter prompt style matching the teal apple aesthetic
src = src.replace(
    '"Surrealist fine art photography, hyperrealistic, 8k. "',
    '"Fine art surrealist photography, medium format film aesthetic, hyperrealistic. "'
)
src = src.replace(
    '"Completely monochromatic grayscale background and environment, {env}. "',
    '"Complete monochrome world — every surface, wall, object in pure silver-grey desaturated tones, {env}. "'
)
src = src.replace(
    '"but the object casting it is completely absent — only the shadow exists, "',
    '"but its source is entirely absent from the scene — only the shadow remains, "'
)
src = src.replace(
    '"rendered in vivid {color_desc} — the ONLY color in the entire image. "',
    '"rendered in rich saturated {color_desc} — the sole point of color in an otherwise colorless world. "'
)

with open("/data/data/com.termux/files/home/omega_nft_engine.py", "w") as f:
    f.write(src)

print("Patch applied")
