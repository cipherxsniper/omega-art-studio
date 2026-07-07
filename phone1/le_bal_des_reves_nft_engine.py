#!/usr/bin/env python3
"""
LE BAL DES RÊVES — NFT Engine v1.0
Thomas Lee Harvey · Omega AI · OM109 Authenticated

Fifth collection in the Omega NFT system. 100 impossible surrealist
characters at an eternal masked ball. Card-grading rarity ladder
(Impossible Diamond / Gold / Silver / Bronze / Common) instead of the
named-tier system used in Echoes of Eternity, so this collection has
its own visual signature in the UI.

Built to plug into the existing pipeline pattern from omega_nft_final.py:
same image-gen approach (Pollinations/Flux), same post-processing,
same OM109 dual-signature + chain-hash provenance, same nft_registry
schema. Differences are called out inline with NOTE: comments.
"""

import os, sys, json, time, random, hashlib, argparse, uuid, psycopg2
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.parse import quote

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ── PATHS ────────────────────────────────────────────────────────────
BASE = Path.home() / "le_bal_des_reves"
IMAGES_DIR = BASE / "images"
META_DIR = BASE / "metadata"
LEDGER_LOG = BASE / "om109_ledger.jsonl"
for d in [IMAGES_DIR, META_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── DB CONNECTIONS ───────────────────────────────────────────────────
PG_LEDGER = "dbname=omega_ledger user=postgres host=127.0.0.1 port=5544"

COLLECTION_NAME = "Le Bal des Rêves"
TOTAL_SUPPLY = 100

# NOTE: scoped genesis seed for this collection specifically, same
# pattern as Echoes (tied to Thomas's birthday constant 10/9 via OM109,
# but with a collection-specific salt so chain hashes don't collide
# across collections).
OMEGA_GENESIS_SEED = "OMEGA_GENESIS_THOMAS_LEE_HARVEY_OM109_LE_BAL_DES_REVES_2026"
_LAST_CHAIN_HASH = "OMEGA_LE_BAL_DES_REVES_GENESIS"

# ── 13 FOUNDING WALLETS (from omega_provenance_api.py NFT_WALLET_MAP) ─
FOUNDING_WALLETS = [
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
THOMAS_WALLET = FOUNDING_WALLETS[0]

# ══════════════════════════════════════════════════════════════════
# TRAIT POOLS — combined space is large enough that 100 unique full
# combinations is trivial; the uniqueness tracker in get_character()
# still verifies no duplicate combo is ever assigned, deterministically.
# ══════════════════════════════════════════════════════════════════

# Each archetype is (name, head/face description, default accent hint)
# NOTE: "The Twin Pair" appears exactly once in this pool and is locked
# to a single specific token via TWIN_PAIR_TOKEN below — it is one card,
# not two, and carries no gendered or personal-identity framing: two
# impossible adult figures in formal eveningwear, standing back-to-back,
# both faces toward the viewer, skin of living cloud and open sky.
ARCHETYPES = [
    ("The Gramophone Oracle", "head is an antique gramophone horn that blooms into living human eyes staring back at the viewer"),
    ("The Stag-Headed Ledger Keeper", "enormous stag head with antlers made of glowing chain-hash glyphs, small drawers open in the flesh of the neck revealing miniature versions of the same figure"),
    ("The Birdcage Veil", "head and upper face enclosed in an ornate golden birdcage, small impossible birds made of cloud and sky circling slowly inside"),
    ("The Multi-Mask Reversal", "four fused masks forming one face, each showing a different impossible expression"),
    ("The Twin Pair", "two impossible figures standing back-to-back, both faces looking directly at the viewer at once, skin made of living clouds and open blue sky with faint drifting ledger pages dissolving in the vapor"),
    ("The Moth Crown", "crowned by enormous moth wings made of stained glass, light refracting in shifting colors"),
    ("The Hourglass Throat", "neck elongated into a glass hourglass filled with slow-drifting smoke instead of sand"),
    ("The Compass Face", "face replaced by an antique brass compass with no needle, the rose endlessly slowly rotating"),
    ("The Chandelier Antler", "antlers dripping with melted candle wax like an inverted chandelier"),
    ("The Key-Toothed Smile", "mouth filled with small golden keys in place of teeth"),
    ("The Lantern Skull", "skull rendered as an antique lantern containing a living firefly galaxy"),
    ("The Porcelain Hand Mask", "face is a single cracked porcelain hand, cupping a small pool of still water"),
    ("The Crow Crown", "a single large crow perched where the head should be, wings spread like a dark halo"),
    ("The Spiral Staircase Spine", "spine visible through an open back panel of the costume, forming a small spiral staircase with no supporting structure"),
    ("The Typewriter Jaw", "lower jaw built from an antique typewriter, keys in place of teeth"),
    ("The Jellyfish Veil", "veil made of glowing jellyfish tendrils drifting as though underwater despite the still ballroom air"),
    ("The Second Moon Eye", "one eye replaced by a small glowing crescent moon"),
    ("The Wolf-Shadow Cloak", "a cloak that casts the shadow of a wolf, though no wolf is present to cast it"),
    ("The Violin Ribcage", "ribcage open at the chest, a small violin resting where the heart should be"),
    ("The Mirror Shard Crown", "a crown built from shattered mirror shards, each shard reflecting a different room of the ballroom"),
    ("The Pocket-Watch Heart", "chest cavity open, revealing a ticking pocket watch with a mirrored face instead of numerals"),
    ("The Orchid Throat", "throat blooming into a single mercury-dewed orchid"),
    ("The Submarine Periscope Eye", "one eye is a small brass periscope emerging from the skin"),
    ("The Chess Piece Hand", "one hand carved entirely from black obsidian in the shape of a chess piece"),
    ("The Letter-Sealed Mouth", "mouth sealed with dripping wax that flows upward, a hidden folded letter just visible beneath"),
    ("The Antique Diving Helmet", "head fully enclosed in a brass diving helmet, the interior filled with slowly drifting stars"),
    ("The Cracked Globe Skull", "skull rendered as a cracked antique globe, faint golden light leaking from the oceans"),
    ("The Marionette Strings", "fine strings extend from every major joint upward into the ballroom ceiling, no puppeteer ever visible"),
    ("The Static Storm Veil", "a veil crackling with frozen lightning that never quite moves"),
    ("The Folded Map Face", "face rendered as an old folded map, the creases forming the eyes and mouth"),
    ("The Sundial Cheekbone", "one cheekbone carved as a working brass sundial, a thin shadow creeping slowly across the jaw"),
    ("The Quill-Feather Wing", "one arm dissolves into a single enormous black quill feather, faint handwriting bleeding across the plume"),
    ("The Inkwell Throat", "throat hollowed into a crystal inkwell, slow black ink rising and falling like breath"),
    ("The Astrolabe Halo", "head crowned by a slowly rotating brass astrolabe, tiny constellations etched into its rings"),
    ("The Sealing-Wax Eye", "one eye replaced by a perfect drop of dark red sealing wax, a faint crest pressed into its surface"),
    ("The Hourglass Ribs", "ribcage open to reveal a slim hourglass where the heart should be, sand falling impossibly sideways"),
    ("The Tarot Spine", "spine visible through an open seam, each vertebra a tiny painted tarot card"),
    ("The Candlewax Crown", "crown formed from frozen, dripping candlewax, a single flame still burning at its peak"),
    ("The Telescoping Neck", "neck extends in brass telescoping rings like an antique spyglass, slightly too tall for the room"),
    ("The Music-Box Sternum", "chest opens like a music box lid, a tiny mechanical dancer spinning silently inside"),
    ("The Cartographer's Palm", "one palm open and tattooed with a fine antique map, the lines slowly redrawing themselves"),
    ("The Lacquered Raven Mask", "face entirely obscured by a lacquered black raven mask, the beak slightly parted in silence"),
    ("The Bellows Lung", "one side of the chest is an exposed antique bellows, slowly expanding and contracting with breath"),
    ("The Stained-Glass Throat", "throat rendered as a small stained-glass window, candlelight glowing faintly through from within"),
    ("The Cameo Profile", "one half of the face is a raised ivory cameo profile of a stranger, fused seamlessly to living skin"),
    ("The Brass Knuckle Crown", "crown welded from antique brass knuckles, polished smooth and catching every candle flame"),
    ("The Veiled Hourglass Face", "entire face obscured behind a thin veil with an hourglass shape woven into the lace"),
    ("The Cracked Porcelain Spine", "spine made of stacked cracked porcelain discs, faint gold kintsugi seams glowing between them"),
    ("The Match-Head Fingertips", "all ten fingertips tipped with tiny unlit matchheads, one faintly smoking"),
    ("The Brass Locket Sternum", "sternum opens like a locket, revealing a tiny rotating portrait of an unfamiliar face"),
    ("The Eclipsed Monocle", "wears a single monocle showing a tiny eclipse in permanent slow motion"),
    ("The Wickerwork Jaw", "lower jaw woven entirely from fine antique wicker, faint candlelight visible through the gaps"),
    ("The Folded Fan Wings", "both shoulder blades sprout antique folding fans in place of wings, slowly opening and closing"),
    ("The Powdered Wig Storm", "an towering powdered wig that occasionally flickers with tiny contained lightning"),
    ("The Silver Thimble Fingers", "each finger capped in a tarnished silver thimble engraved with a different tiny number"),
    ("The Snuffbox Heart", "chest opens to reveal an antique snuffbox where the heart should be, lid gently rising and falling"),
    ("The Etched Monocle Skull", "skull etched all over with fine engraved filigree, one eye socket holding a monocle of smoke"),
    ("The Wax Seal Lips", "lips fused shut beneath a perfect circular wax seal bearing an unreadable crest"),
    ("The Birdsong Music Box", "throat opens like a tiny music box, a faint mechanical birdsong audible from within"),
    ("The Folding Screen Torso", "torso constructed from a hinged antique folding screen, painted scenes shifting as it moves"),
    ("The Carved Ivory Lattice Face", "face is an intricate carved ivory lattice, candlelight passing through in shifting patterns"),
    ("The Pendulum Throat", "throat houses a small swinging pendulum visible through translucent skin"),
    ("The Gilded Antler Crown", "crowned with gilded antlers strung with tiny unlit chandelier crystals"),
    ("The Buttoned Ribcage", "ribcage rendered as a row of ornate antique buttons, slightly ajar at the center"),
    ("The Embroidered Eye Patch", "one eye covered by a heavily embroidered patch depicting a smaller version of the same ballroom"),
    ("The Hinged Jaw Box", "lower jaw is a small hinged wooden box, faint golden light leaking from the seam"),
    ("The Spinning Coin Eyes", "both eyes replaced by slowly spinning antique coins, faces never quite visible"),
    ("The Lace Spiderweb Hands", "both hands rendered in fine antique lace shaped like spiderwebs, motionless dew caught in the threads"),
    ("The Tin Soldier Spine", "spine constructed from a column of stacked tin soldiers, frozen mid-march"),
    ("The Folded Crane Shoulders", "both shoulders fold into the shape of large origami cranes, paper-thin and faintly glowing"),
    ("The Brass Gear Throat", "throat filled with visible interlocking brass gears, slowly turning beneath translucent skin"),
    ("The Painted Porcelain Doll Face", "face rendered as a cracked antique painted porcelain doll, eyes slightly too wide"),
    ("The Velvet Curtain Cloak", "cloak made of heavy velvet stage curtain, slowly parting to reveal a smaller hidden ballroom"),
    ("The Etched Compass Sternum", "sternum etched with a compass rose, a faint needle spinning beneath the skin"),
    ("The Cracked Hourglass Crown", "crowned with a large cracked hourglass, fine golden sand drifting into the hair"),
    ("The Silver Spoon Smile", "smile lined with small antique silver spoons in place of teeth, each engraved differently"),
    ("The Stitched Map Cloak", "cloak stitched entirely from antique maps of places that no longer exist"),
    ("The Brass Birdcage Ribs", "ribcage opens into a small brass birdcage, a single unlit candle suspended within"),
    ("The Painted Eye Fan", "carries a folding fan painted with a single enormous watching eye"),
    ("The Wax-Dripped Crown of Quills", "crown of black quills dripping slow wax instead of ink"),
    ("The Marbled Porcelain Throat", "throat rendered in marbled porcelain, fine cracks forming a map of unfamiliar coastlines"),
    ("The Folded Letter Sternum", "sternum opens to reveal an endlessly folding and unfolding antique letter, the words never quite legible"),
    ("The Silver Filigree Antlers", "antlers made of impossibly fine silver filigree, faint bells visible at each tip"),
    ("The Brass Hourglass Eyes", "both eyes are small brass hourglasses, fine sand falling in opposite directions"),
    ("The Lacquered Fan Crown", "crowned by an array of black lacquered fans arranged like peacock feathers"),
    ("The Stitched Glove Heart", "chest opens to reveal a single antique stitched glove cupped where the heart should be"),
    ("The Carved Bone Lattice Mask", "mask carved from fine bone lattice, candlelight catching every intricate gap"),
    ("The Folding Mirror Wings", "both shoulder blades fold outward into hinged mirror panels, reflecting fractured ballroom light"),
    ("The Tarnished Locket Eyes", "both eyes replaced by small tarnished silver lockets, faintly ajar"),
    ("The Wrought Iron Vine Crown", "crowned by wrought iron vines slowly blooming with small glass roses"),
    ("The Brocade Storm Cloak", "cloak woven from heavy antique brocade that occasionally ripples like a contained storm"),
    ("The Pressed Flower Lattice Face", "face is a fine lattice of pressed antique flowers under glass"),
    ("The Carved Driftwood Spine", "spine constructed from smooth carved driftwood, faintly sea-worn despite the ballroom setting"),
    ("The Antique Key Ribcage", "ribcage formed from dozens of fused antique keys, none matching the same lock"),
    ("The Folded Silk Throat", "throat wrapped endlessly in folding antique silk, the folds shifting on their own"),
    ("The Etched Glass Heart", "chest opens to reveal a heart of finely etched glass, candlelight scattering through the engravings"),
    ("The Powdered Moth Shoulders", "both shoulders dusted in fine moth-wing powder, faint silver trails left with every movement"),
    ("The Carved Alabaster Profile", "half the face carved in pale alabaster, fused seamlessly to the living half"),
    ("The Brass Compass Crown", "crowned by an oversized brass compass, the needle slowly tracing the rim"),
    ("The Wax-Sealed Eye Locket", "wears a small locket over one eye, sealed shut with a circle of dark wax"),
    ("The Stitched Constellation Cloak", "cloak embroidered with a constellation map that subtly rearranges itself"),
    ("The Folding Fan Spine", "spine constructed from a column of stacked antique folding fans, slowly opening in sequence"),
]

COSTUME_MATERIALS = [
    "a formal black-tie ensemble woven from open ledger pages that smolder at the edges but never fully catch fire",
    "a gown that dissolves into fine mist at the hem",
    "a suit stitched from vanishing, faintly rotating gallery links",
    "a tailcoat lined with diamond tears frozen mid-fall",
    "a gown woven from threadbare cloud-fiber that ignites into quiet flame at the cuffs",
    "a suit made of cracked mirror panels, each reflecting the viewer back",
    "a gown constructed from antique sheet music, individual notes lifting off the fabric",
    "a tailcoat embroidered with cryptographic signatures that fade in and out of visibility",
    "a gown made of preserved butterfly wings that slowly open and close",
    "a suit cut from aged parchment maps, faint glowing routes tracing the seams",
    "a gown of fine woven spiderweb strung with motionless morning dew",
    "a tailcoat made of overlapping antique clock faces, each showing a different hour",
    "a gown stitched from torn, illegible ballroom invitations",
    "a suit made of layered obsidian feathers, each a different shade of black",
    "a gown of liquid mercury fabric that never quite settles into stillness",
    "a tailcoat made of pressed flowers from a garden that no longer exists",
    "a gown built from overlapping playing cards, the suits shifting if watched too long",
    "a suit lined with frozen, mid-drip candle wax",
    "a gown woven from captured threads of starlight",
    "a tailcoat constructed from fused antique vault keys",
]

ACCENT_DETAILS = [
    "one hand rendered entirely in quiet fire, the other in turning ledger pages",
    "diamond tears falling upward instead of down",
    "a single faintly rotating gallery link orbiting the figure like a halo",
    "a chain-hash bracelet that appears to rewrite itself every few seconds",
    "a small trailing flock of paper moths following every movement",
    "a floating pocket ledger that writes itself in real time, just out of focus",
    "a shadow that lags a half-second behind the figure's true position",
    "a thin trail of golden numerals spilling quietly from one sleeve",
    "a single candle flame burning sideways, defying the room's gravity",
    "a cracked hourglass worn as a brooch, its sand flowing upward",
    "fingertips that leave the faintest afterimage in the air",
    "a thread of smoke that briefly forms readable words before dispersing",
    "a small caged firefly galaxy pinned to the lapel",
    "two shadows cast in opposite directions at once",
    "a faint second heartbeat audible just beneath the music",
    "a key that seems to exist in the hand only when no one looks directly at it",
    "fine threads of static light crawling slowly along every seam",
    "the faint outline of a constellation visible just beneath the skin of one hand",
]

PERSPECTIVES = [
    "three-quarter angle beneath the grand chandeliers of the ballroom, dramatic chiaroscuro lighting",
    "low angle looking up past shattered, floor-length mirrors",
    "wide establishing view of the mirrored hall, the figure small against the impossible architecture",
    "extreme close-up, the figure filling most of the frame, background dissolved into soft shadow",
    "overhead view looking down across the ballroom floor, the figure centered amid cobweb labyrinths",
    "eye-level, centered, classical portrait composition with melting chandeliers visible behind",
    "dutch-angle tilt, faintly unsettling, mirrors reflecting infinite versions of the same hall",
    "side profile beneath candlelight, long shadow stretching across a cracked marble floor",
]

# ── RARITY LADDER (card-grading system, distinct from the other 4 collections) ──
# Impossible Diamond — 1 of 1, fixed seeded token, thin diamond liner in UI
# Gold               — ultra rare, gold liner
# Silver             — rare, silver liner
# Bronze             — medium, bronze liner
# Common             — no liner
RARITY_BORDER = {
    "Impossible Diamond": "diamond_liner",
    "Gold": "gold_liner",
    "Silver": "silver_liner",
    "Bronze": "bronze_liner",
    "Common": "none",
}

_rng_diamond = random.Random(OMEGA_GENESIS_SEED + "_IMPOSSIBLE")
IMPOSSIBLE_DIAMOND_TOKEN = _rng_diamond.randint(1, TOTAL_SUPPLY)

# Lock "The Twin Pair" archetype to its own dedicated, seeded token so it
# appears exactly once in the collection, deterministically.
_rng_twin = random.Random(OMEGA_GENESIS_SEED + "_TWIN_PAIR")
_twin_candidates = [t for t in range(1, TOTAL_SUPPLY + 1) if t != IMPOSSIBLE_DIAMOND_TOKEN]
TWIN_PAIR_TOKEN = _rng_twin.choice(_twin_candidates)


def get_rarity(token_id):
    if token_id == IMPOSSIBLE_DIAMOND_TOKEN:
        return "Impossible Diamond", 6
    r = random.Random(token_id * 9001).random()
    if r < 0.02:
        return "Gold", 5
    elif r < 0.15:
        return "Silver", 4
    elif r < 0.50:
        return "Bronze", 3
    else:
        return "Common", 2


_used_combos = set()
_used_archetype_names = set()


def get_character(token_id):
    """Deterministically pick a unique trait combination for this token.
    Rerolls (deterministically, by incrementing a salt) on collision so
    no two tokens in the 100-piece run share an identical full combo."""
    if token_id == TWIN_PAIR_TOKEN:
        archetype = ARCHETYPES[4]  # "The Twin Pair", locked
    else:
        non_twin_archetypes = [a for i, a in enumerate(ARCHETYPES) if i != 4]
        salt0 = 0
        while True:
            r0 = random.Random(token_id * 7919 + salt0)
            idx = r0.randrange(len(non_twin_archetypes))
            archetype = non_twin_archetypes[idx]
            if archetype[0] not in _used_archetype_names:
                _used_archetype_names.add(archetype[0])
                break
            salt0 += 1

    salt = 0
    while True:
        r = random.Random(token_id * 104729 + salt)
        costume = COSTUME_MATERIALS[r.randrange(len(COSTUME_MATERIALS))]
        accent = ACCENT_DETAILS[r.randrange(len(ACCENT_DETAILS))]
        perspective = PERSPECTIVES[r.randrange(len(PERSPECTIVES))]
        combo_key = (archetype[0], costume, accent, perspective)
        if combo_key not in _used_combos:
            _used_combos.add(combo_key)
            return archetype, costume, accent, perspective
        salt += 1


def build_prompt(token_id):
    (name, head_desc), costume, accent, perspective = get_character(token_id)
    prompt = (
        f"Hyper-detailed photorealistic hypersurreal masterpiece, museum-grade fine art photography, "
        f"shot on macro lens, extreme close-focus clarity, every fiber and pore tack-sharp, "
        f"12k resolution, {perspective}. An impossible figure at the eternal masked ball Le Bal des Rêves "
        f"inside a grand mirrored château hall. The figure's {head_desc}. "
        f"They wear {costume}. Notable detail: {accent}. "
        f"Dramatic chiaroscuro lighting, melting chandeliers, shattered mirrors reflecting infinite "
        f"versions of the scene, faint cobweb labyrinths in the corners, razor-sharp obsessive micro-detail "
        f"on every impossible texture — individual threads, pores, and surface grain crisply resolved — "
        f"no softness, no blur, no haze. Collector fine art NFT, no text, no watermark, "
        f"no signature, full frame edge to edge, no black borders."
    )
    negative = (
        "cartoon,anime,painting,illustration,low quality,blurry,text,watermark,signature,border,"
        "ugly,deformed,extra limbs,black bars,letterbox,padding"
    )
    return name, prompt, negative, (head_desc, costume, accent)


# ══════════════════════════════════════════════════════════════════
# IMAGE GENERATION / POST-PROCESSING — same approach as omega_nft_final.py
# ══════════════════════════════════════════════════════════════════

def generate_image(token_id, prompt, negative):
    out_path = IMAGES_DIR / f"{token_id:04d}.png"
    if out_path.exists():
        print(f"  image {token_id:04d} exists, skipping")
        return out_path, False
    seed = token_id * 211 + 17
    url = (
        f"https://image.pollinations.ai/prompt/{quote(prompt)}"
        f"?width=768&height=1024&seed={seed}&steps=50&negative={quote(negative)}"
        f"&model=flux&nologo=true&enhance=true"
    )
    print(f"  generating #{token_id:04d}...")
    for attempt in range(1, 4):
        try:
            with urlopen(Request(url, headers={"User-Agent": "OmegaNFT/LeBalDesReves/1.0"}), timeout=150) as r:
                data = r.read()
            with open(out_path, "wb") as f:
                f.write(data)
            print(f"  saved {out_path.name} ({len(data)//1024}KB)")
            return out_path, True
        except Exception as e:
            print(f"  attempt {attempt}/3: {e}")
            if attempt < 3:
                time.sleep(12 * attempt)
    return None, False


def post_process(img_path):
    if not PIL_OK:
        return img_path
    img = Image.open(img_path).convert("RGB")
    img = ImageEnhance.Contrast(img).enhance(1.32)
    img = ImageEnhance.Brightness(img).enhance(1.04)
    img = ImageEnhance.Color(img).enhance(2.05)
    img = img.filter(ImageFilter.SHARPEN)
    img.save(img_path, optimize=True, quality=99)
    return img_path


def add_diamond_or_metal_liner_marker(img_path, rarity):
    """Adds a thin, subtle pixel-level border indicator on the source image
    itself, matching the rarity tier. This is a baseline visual cue baked
    into the file; the live gallery UI should still render its own crisp
    CSS/SVG border on top of this using the `border_tier` metadata field,
    since a UI-level border will look sharper than anything baked into a
    raster image."""
    if not PIL_OK:
        return img_path
    colors = {
        "Impossible Diamond": (210, 235, 255),  # pale diamond-blue
        "Gold": (212, 175, 55),
        "Silver": (192, 192, 200),
        "Bronze": (140, 90, 50),
    }
    if rarity not in colors:
        return img_path
    img = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    thickness = 3 if rarity == "Impossible Diamond" else 4
    draw.rectangle([0, 0, w - 1, h - 1], outline=colors[rarity], width=thickness)
    img.save(img_path, optimize=True, quality=99)
    return img_path


def hash_image(img_path):
    with open(img_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def om109_sign(token_id, image_hash):
    genesis = hashlib.sha256(OMEGA_GENESIS_SEED.encode()).hexdigest()
    sig_a = hashlib.sha256(f"{genesis}:A:{token_id}:{image_hash}".encode()).hexdigest()
    sig_b = hashlib.sha256(f"{genesis}:B:{token_id}:{image_hash}:{sig_a}".encode()).hexdigest()
    fp = hashlib.sha256(f"{sig_a[:32]}{sig_b[:32]}".encode()).hexdigest()
    return {"sig_a": sig_a, "sig_b": sig_b, "om109_fingerprint": fp}


def chain_hash_entry(entry):
    global _LAST_CHAIN_HASH
    entry["prev_chain_hash"] = _LAST_CHAIN_HASH
    h = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
    entry["chain_hash"] = h
    _LAST_CHAIN_HASH = h
    return h


def log_jsonl(entry):
    with open(LEDGER_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ══════════════════════════════════════════════════════════════════
# AUDIT LOG — mint is a creation event, not a value transfer, so it
# belongs in audit_log, not ledger_entries. (Matches the fix applied
# to list_nft_for_auction() in omega_marketplace.py tonight — see
# Section 5.6 / 5.7 of the engineering handoff. omega_nft_final.py's
# ledger_mint_psql() writes a $0.00 row to ledger_entries for the same
# kind of non-transfer event; recommend backporting this same fix to
# the other 4 collections' mint scripts for consistency.)
# ══════════════════════════════════════════════════════════════════

def audit_log_mint(token_id, owner_wallet, rarity, om109_fp, name):
    try:
        conn = psycopg2.connect(PG_LEDGER)
        cur = conn.cursor()
        entry_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO audit_log (id, actor, action, entity_type, entity_id, details)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            entry_id, owner_wallet, "NFT_MINT", "nft_registry", f"{COLLECTION_NAME}:{token_id}",
            json.dumps({
                "collection": COLLECTION_NAME,
                "token_id": token_id,
                "card_name": name,
                "rarity": rarity,
                "om109_fingerprint": om109_fp,
            })
        ))
        conn.commit()
        cur.close()
        conn.close()
        print(f"  audit_log: recorded mint #{token_id:04d}")
    except Exception as e:
        print(f"  audit_log: offline or failed ({e}) — JSONL chain log still written")


def register_in_nft_registry(token_id, owner_wallet, name, rarity, theme, image_hash,
                              om109, chain_hash, is_founder_linked=False):
    """Insert into nft_registry using the real composite key (collection, token_id).
    Stripe fields are left NULL here deliberately — wire this up to your
    existing Stripe NFT scripts (omega_stripe_nft.py / patch_collection_stripe.py)
    separately, since this engine hasn't seen those scripts' interfaces and
    shouldn't guess at them."""
    try:
        conn = psycopg2.connect(PG_LEDGER)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO nft_registry
            (token_id, name, title, rarity, theme, image_sha256, om109_fingerprint,
             om109_sig_a, om109_sig_b, chain_hash, owner_account_id, is_founder_linked,
             sale_status, minted_at, collection)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            ON CONFLICT (collection, token_id) DO NOTHING
        """, (
            token_id, name, name, rarity, theme, image_hash,
            om109["om109_fingerprint"], om109["sig_a"], om109["sig_b"], chain_hash,
            owner_wallet, is_founder_linked, "founder_held" if is_founder_linked else "unsold",
            COLLECTION_NAME,
        ))
        conn.commit()
        cur.close()
        conn.close()
        print(f"  nft_registry: recorded #{token_id:04d} -> owner {owner_wallet[:8]}...")
    except Exception as e:
        print(f"  nft_registry: FAILED ({e})")


# ══════════════════════════════════════════════════════════════════
# FOUNDING WALLET ASSIGNMENT — 13 wallets, each gets exactly 1 token,
# genesis-seeded for reproducibility/auditability. Thomas's wallet is
# guaranteed the Impossible Diamond token specifically.
# ══════════════════════════════════════════════════════════════════

def assign_founding_wallets():
    rng = random.Random(OMEGA_GENESIS_SEED + "_WALLET_ASSIGNMENT")
    other_wallets = [w for w in FOUNDING_WALLETS if w != THOMAS_WALLET]
    remaining_tokens = [t for t in range(1, TOTAL_SUPPLY + 1) if t != IMPOSSIBLE_DIAMOND_TOKEN]
    rng.shuffle(remaining_tokens)
    chosen = remaining_tokens[: len(other_wallets)]

    assignment = {THOMAS_WALLET: IMPOSSIBLE_DIAMOND_TOKEN}
    for wallet, token in zip(other_wallets, chosen):
        assignment[wallet] = token
    return assignment


# ══════════════════════════════════════════════════════════════════
# METADATA + MINT ORCHESTRATION
# ══════════════════════════════════════════════════════════════════

def build_metadata(token_id, name, rarity, theme, image_hash, om109_fp, chain_hash, border_tier):
    minted_at = datetime.now(timezone.utc).isoformat()
    return {
        "name": f"{COLLECTION_NAME} — {name} #{token_id:04d}",
        "description": (
            f"\"{name}\" is a 1-of-{TOTAL_SUPPLY} surrealist fine art NFT from the {COLLECTION_NAME} "
            f"collection by Thomas Lee Harvey, an eternal masked ball where every figure is a distinct "
            f"impossible riddle. Rarity: {rarity}."
        ),
        "image": f"ipfs://YOUR_CID/le_bal_des_reves/images/{token_id:04d}.png",
        "external_url": "https://omegaops.ai",
        "edition": token_id,
        "total_supply": TOTAL_SUPPLY,
        "rarity": rarity,
        "border_tier": border_tier,
        "creator": "Thomas Lee Harvey",
        "collection": COLLECTION_NAME,
        "minted_at": minted_at,
        "image_sha256": image_hash,
        "om109_fingerprint": om109_fp,
        "om109_chain_hash": chain_hash,
        "authentication": "OM109 Alternating Dual-Key Signature",
        "attributes": [
            {"trait_type": "Rarity", "value": rarity},
            {"trait_type": "Border Tier", "value": border_tier},
            {"trait_type": "Card Name", "value": name},
            {"trait_type": "Edition", "value": f"{token_id} of {TOTAL_SUPPLY}"},
            {"trait_type": "Creator", "value": "Thomas Lee Harvey"},
            {"trait_type": "Collection", "value": COLLECTION_NAME},
            {"trait_type": "Authentication", "value": "OM109 Dual-Signature"},
            {"trait_type": "SHA256 Fingerprint", "value": image_hash},
            {"trait_type": "Year", "value": "2026"},
        ],
    }


def mint_token(token_id, owner_wallet=None, is_founder_linked=False):
    print(f"\n{'='*56}\n  MINTING  #{token_id:04d} — {COLLECTION_NAME}\n{'='*56}")
    rarity, _ = get_rarity(token_id)
    name, prompt, negative, theme_parts = build_prompt(token_id)
    theme = theme_parts[0]
    border_tier = RARITY_BORDER[rarity]
    print(f"  Card    : {name}\n  Rarity  : {rarity}  ({border_tier})")

    img_path, was_fresh = generate_image(token_id, prompt, negative)
    if not img_path:
        return False
    if was_fresh:
        post_process(img_path)
        add_diamond_or_metal_liner_marker(img_path, rarity)
    else:
        print(f"  image {token_id:04d} already exists — skipping post-process to avoid re-applying effects")

    image_hash = hash_image(img_path)
    om109 = om109_sign(token_id, image_hash)
    ts = datetime.now(timezone.utc).isoformat()

    chain_entry = {
        "event_type": "NFT_MINT",
        "token_id": token_id,
        "collection": COLLECTION_NAME,
        "card_name": name,
        "rarity": rarity,
        "om109_fingerprint": om109["om109_fingerprint"],
        "minted_at": ts,
    }
    chash = chain_hash_entry(chain_entry)
    log_jsonl(chain_entry)

    owner_wallet = owner_wallet or THOMAS_WALLET
    audit_log_mint(token_id, owner_wallet, rarity, om109["om109_fingerprint"], name)
    register_in_nft_registry(token_id, owner_wallet, name, rarity, theme, image_hash,
                              om109, chash, is_founder_linked=is_founder_linked)

    meta = build_metadata(token_id, name, rarity, theme, image_hash,
                           om109["om109_fingerprint"], chash, border_tier)
    with open(META_DIR / f"{token_id:04d}.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"  OM109   : {om109['om109_fingerprint'][:32]}...\n  Chain   : {chash[:32]}...\n  MINTED  : {name} #{token_id:04d} - {rarity}")
    return True


def verify_ledger():
    if not LEDGER_LOG.exists():
        print("No ledger found.")
        return
    entries = [json.loads(l) for l in open(LEDGER_LOG) if l.strip()]
    print(f"\nVerifying {len(entries)} chain entries...")
    errors = 0
    prev = "OMEGA_LE_BAL_DES_REVES_GENESIS"
    for e in entries:
        if e.get("prev_chain_hash") != prev:
            print(f"  CHAIN BREAK #{e['token_id']}")
            errors += 1
        prev = e.get("chain_hash", "")
    print(f"  {'ALL CLEAN' if not errors else str(errors)+' ERRORS'} - {len(entries)} entries")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--id", type=int, default=None)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--assign-wallets", action="store_true",
                         help="Print the genesis-seeded founding wallet -> token assignment without minting")
    parser.add_argument("--mint-with-wallets", action="store_true",
                         help="Mint all 100 and assign each token to its genesis-seeded owner wallet")
    args = parser.parse_args()

    print(f"\n {COLLECTION_NAME.upper()} v1.0 - Thomas Lee Harvey - Omega AI")
    print(f" Output: {BASE}\n")
    print(f" Impossible Diamond token: #{IMPOSSIBLE_DIAMOND_TOKEN:04d}")
    print(f" Twin Pair token:          #{TWIN_PAIR_TOKEN:04d}\n")

    if args.verify:
        verify_ledger()
        return

    if args.assign_wallets:
        assignment = assign_founding_wallets()
        for wallet, token in assignment.items():
            label = "Thomas Lee Harvey (Impossible Diamond)" if wallet == THOMAS_WALLET else wallet
            print(f"  {label} -> token #{token:04d}")
        return

    if args.id:
        mint_token(args.id)
        return

    if args.mint_with_wallets:
        assignment = assign_founding_wallets()
        token_to_wallet = {t: w for w, t in assignment.items()}
        existing = {int(f.stem) for f in IMAGES_DIR.glob("*.png")}
        success = 0
        t0 = time.time()
        for i in range(1, TOTAL_SUPPLY + 1):
            owner = token_to_wallet.get(i, THOMAS_WALLET)  # non-founding tokens default to Thomas until sold
            is_founder = i in token_to_wallet
            if i in existing:
                print(f"  skip #{i:04d} - already minted")
                success += 1
                continue
            if mint_token(i, owner_wallet=owner, is_founder_linked=is_founder):
                success += 1
            time.sleep(2)
        print(f"\n COMPLETE: {success}/{TOTAL_SUPPLY} | {time.time()-t0:.0f}s")
        return

    existing = {int(f.stem) for f in IMAGES_DIR.glob("*.png")}
    success = 0
    t0 = time.time()
    for i in range(args.start, args.start + args.count):
        if i in existing:
            print(f"  skip #{i:04d} - already minted")
            success += 1
            continue
        if mint_token(i):
            success += 1
        if i < args.start + args.count - 1:
            time.sleep(2)
    print(f"\n COMPLETE: {success}/{args.count} | {time.time()-t0:.0f}s\n Images: {IMAGES_DIR}\n Ledger: {LEDGER_LOG}\n")


if __name__ == "__main__":
    main()

