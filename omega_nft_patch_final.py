path = '/data/data/com.termux/files/home/omega_nft_final.py'
src = open(path).read()

# Fix dimensions to 1024x1024 square — standard NFT format
src = src.replace('WIDTH=1024\nHEIGHT=1024', 'WIDTH=1024\nHEIGHT=1024')

# Fix the URL to force square
src = src.replace(
    'f"?width=768&height=1024&seed={seed}&steps={steps}',
    'f"?width=1024&height=1024&seed={seed}&steps={steps}'
)

# Nuclear prompt update — describe the teal apple photo exactly
old_prompt = '''    prompt=(
        f"Fine art studio photograph, 8K ultra-sharp, {perspective}. "
        f"BRIGHT warm light grey background wall, smooth concrete studio surface — "
        f"think gallery white-grey, NOT dark, NOT black, NOT atmospheric. "
        f"Single hard angled light source from upper left creates one razor-sharp shadow "
        f"of {shadow_desc} on the bright grey wall behind — "
        f"the shadow is large, dramatic, perfectly defined, "
        f"but the object that casts it is completely invisible, absent, does not exist in frame. "
        f"On the grey studio surface in the foreground: {subject_desc}. "
        f"The subject is drenched in individual photorealistic water droplets — "
        f"each droplet a perfect glass sphere refracting light, sweating condensation, "
        f"micro-detail on every droplet, crystal clear refraction like a cold object in warm air. "
        f"The entire subject glows in rich saturated {color_desc} — "
        f"this is the ONE AND ONLY color in the image. "
        f"Every other element — wall, floor, shadow, surface — is desaturated silver-grey monochrome. "
        f"The contrast between the vivid saturated {color_desc} subject "
        f"and the completely grey world around it is the entire visual statement. "
        f"Hasselblad medium format lens, f/2.8, tack sharp subject, "
        f"soft grey studio bokeh background, shallow depth of field. "
        f"Photorealistic, hyperdetailed, crisp museum print quality. "
        f"NO black backgrounds, NO dark atmosphere, NO smoke, NO darkness. "
        f"Bright clean grey studio environment throughout entire frame. "
        f"NO text, NO watermark, NO borders, NO black bars, NO letterboxing."
    )'''

new_prompt = '''    prompt=(
        f"Commercial product photography meets fine art surrealism. "
        f"Shot on Hasselblad H6D-400C, 100mm macro lens, f/4, ISO 64, studio strobes. "
        f"SQUARE FORMAT 1:1. "
        f"Background: smooth warm grey concrete wall (#B0A898 tone), "
        f"matte grey studio floor — identical to a professional product photography studio. "
        f"Lighting: single Profoto B10 strobe from upper-left at 45 degrees, "
        f"creates one hard-edged razor-sharp shadow of {shadow_desc} "
        f"cast dramatically across the grey wall — "
        f"the object that casts this shadow is COMPLETELY ABSENT from the scene, "
        f"only its shadow is visible, perfectly defined edges, no blur. "
        f"Subject centered in lower two-thirds of frame: {subject_desc}. "
        f"The subject is sweating with condensation — "
        f"hundreds of individual spherical water droplets on its surface, "
        f"each droplet a perfect glass bead refracting light and color, "
        f"micro-sharp detail on every single droplet, "
        f"like a cold object brought into a warm humid room. "
        f"Color: the subject is rendered in deep rich saturated {color_desc} — "
        f"this is the ONLY color in the entire photograph. "
        f"The grey wall, grey floor, the shadow — all completely desaturated monochrome. "
        f"The vivid {color_desc} subject against the grey world is the entire concept. "
        f"Photorealistic RAW photograph, not a painting, not illustration, not CGI render. "
        f"Tack sharp subject, micro detail, photorealistic water refraction. "
        f"Shallow depth of field, soft grey bokeh. "
        f"Square composition, subject fills 40-60 percent of frame. "
        f"NO smoke, NO darkness, NO black, NO atmospheric effects, "
        f"NO text, NO watermark, NO border, NO letterbox bars."
    )'''

if old_prompt in src:
    src = src.replace(old_prompt, new_prompt)
    print("PROMPT PATCHED")
else:
    print("PROMPT NOT FOUND - checking...")
    # Find what's there
    idx = src.find('def build_prompt')
    print(src[idx:idx+200])

# Fix metadata to be complete with all provenance
old_meta = '''def build_metadata(token_id,rarity,title,shadow_desc,subject_desc,color_desc,image_hash,om109_fp,chain_hash):
    palette=["Abyss Monochrome","Dreamfire Void","BioLume Dark","VoidBloom","GoldenVoid"][token_id%5]
    return {"name":f"Echoes of Eternity - {title} #{token_id:04d}","description":f"A surrealist NFT by Thomas Lee Harvey. The shadow of {shadow_desc} dominates a monochrome world, cast by something entirely absent. The only color belongs to {subject_desc}. Authenticated by OM109 dual-signature — the same cryptographic system securing the Omega Bank ledger.","image":f"ipfs://YOUR_CID/images/{token_id:04d}.png","edition":token_id,"rarity":rarity,"title":title,"image_sha256":image_hash,"om109_fingerprint":om109_fp,"chain_hash":chain_hash,"attributes":[{"trait_type":"Rarity","value":rarity},{"trait_type":"Title","value":title},{"trait_type":"Creator","value":"Thomas Lee Harvey"},{"trait_type":"Style","value":"Surreal Abstract Realism"},{"trait_type":"Phantom Shadow","value":shadow_desc},{"trait_type":"Color Subject","value":subject_desc[:50]},{"trait_type":"Accent Color","value":color_desc},{"trait_type":"Palette","value":palette},{"trait_type":"Collection","value":"Echoes of Eternity"},{"trait_type":"Auth","value":"OM109 Dual-Signature"},{"trait_type":"Signed","value":"Yes" if rarity in ("Impossible Diamond","Black Diamond") else "No"}]}'''

new_meta = '''def build_metadata(token_id,rarity,title,shadow_desc,subject_desc,color_desc,image_hash,om109_fp,chain_hash):
    from datetime import datetime,timezone
    palette=["Abyss Monochrome","Dreamfire Void","BioLume Dark","VoidBloom","GoldenVoid"][token_id%5]
    minted_at=datetime.now(timezone.utc).isoformat()
    is_signed = rarity in ("Impossible Diamond","Black Diamond")
    return {
        "name": f"Echoes of Eternity — {title} #{token_id:04d}" if rarity!="Impossible Diamond" else f"Echoes of Eternity — Unique #{token_id:04d}",
        "description": (
            f"\\"{title}\\" is a 1-of-1000 surrealist fine art NFT from the Echoes of Eternity collection "
            f"by Thomas Lee Harvey. "
            f"The shadow of {shadow_desc} dominates a monochrome grey world, "
            f"cast by something entirely absent from the scene. "
            f"The only color in the photograph belongs to {subject_desc}. "
            f"Every token is authenticated by OM109 alternating dual-key signature — "
            f"the same cryptographic primitive securing the Omega Bank distributed ledger. "
            f"Rarity: {rarity}. Edition {token_id} of 1000."
        ),
        "image": f"ipfs://YOUR_CID/images/{token_id:04d}.png",
        "external_url": "https://omegaops.ai",
        "edition": token_id,
        "total_supply": 1000,
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
            {"trait_type":"Edition","value":f"{token_id} of 1000"},
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
    }'''

if old_meta in src:
    src = src.replace(old_meta, new_meta)
    print("METADATA PATCHED")
else:
    print("METADATA NOT FOUND")

open(path,'w').write(src)
