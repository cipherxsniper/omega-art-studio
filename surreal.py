import os, sys, json, random, subprocess, time
from pathlib import Path

# ── DEPENDENCY CHECK ─────────────────────────────────────────────
# No auto-install here. On ARM64 Termux there are no prebuilt wheels for
# torch/diffusers, so pip falls back to compiling from source (numpy,
# cmake, ninja...) and that fails without a full native build toolchain.
# Install these once, manually, before running this script:
#
#   pip install torch diffusers transformers accelerate safetensors Pillow
#
import importlib.util
REQUIRED = ["torch", "diffusers", "transformers", "accelerate", "safetensors", "PIL"]
missing = [m for m in REQUIRED if importlib.util.find_spec(m) is None]
if missing:
    sys.exit(
        "Missing dependencies: " + ", ".join(missing) +
        "\nInstall them first with:\n"
        "  pip install torch diffusers transformers accelerate safetensors Pillow"
    )

import torch
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageChops

# ── CONFIG ──────────────────────────────────────────────────────
OUTPUT_DIR     = "/sdcard/Pictures/Echoes_of_Eternity"
IMAGES_DIR     = OUTPUT_DIR + "/images"
METADATA_DIR   = OUTPUT_DIR + "/metadata"
TOTAL_NFTS     = 1000
WIDTH, HEIGHT  = 768, 768
DEVICE         = "cpu"   # ARM64 phones use CPU inference

os.makedirs(IMAGES_DIR,   exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)

# ── RARITY ──────────────────────────────────────────────────────
def get_rarity(token_id):
    rng = random.Random(token_id * 9999)
    r = rng.random()
    if token_id <= 2 or r < 0.002: return "Black Diamond", 5
    elif r < 0.012:                 return "Super Rare",    4
    elif r < 0.162:                 return "Rare",          3
    elif r < 0.462:                 return "Medium",        2
    else:                           return "Common",        1

# ── SURREALIST CONCEPT ENGINE ────────────────────────────────────
PHANTOM_SHADOWS = [
    ("a cathedral that isn't there",          "a single orchid covered in mercury droplets",         "iridescent violet"),
    ("an hourglass filled with smoke",        "a glass pomegranate weeping crystalline tears",        "deep crimson"),
    ("a lighthouse on an impossible shore",   "a cracked porcelain hand holding still water",        "electric teal"),
    ("a grand piano melting into the floor",  "a golden key dripping liquid amber",                  "liquid gold"),
    ("a throne of bones",                     "a white rose wrapped in barbed wire",                 "bone white and rust"),
    ("a giant eyeball on a pedestal",         "a moth with wings made of stained glass",             "amber and obsidian"),
    ("a clock tower dissolving into birds",   "a compass with no needle floating mid-air",           "verdigris copper"),
    ("a ship sailing through solid ground",   "a glass bottle containing a tiny storm",              "storm grey and lightning blue"),
    ("a figure made entirely of smoke",       "a single match burning upward in zero gravity",       "ember orange"),
    ("a skyscraper made of ice",              "a crow holding a small planet in its beak",           "glacial blue"),
    ("a tree growing downward from the sky",  "a mechanical heart still beating",                    "arterial red"),
    ("an absent dancer mid-leap",             "a ballet shoe filled with black sand",                "pale gold"),
    ("a whale floating above the scene",      "a compass rose carved into a human tooth",            "deep ocean teal"),
    ("a library with no walls",               "a book with pages made of frozen fire",               "ink black and flame"),
    ("a mountain turned upside down",         "a snow globe containing a burning city",              "ash white"),
    ("a giant hand reaching from the floor",  "a pocket watch with a mirror face",                   "antique brass"),
    ("a wolf made of shadow",                 "a lantern containing a living firefly galaxy",        "bioluminescent green"),
    ("a second moon just out of frame",       "a crescent-shaped shard of moonstone",                "lunar silver"),
    ("a doorway to nowhere",                  "a key made of frozen light",                          "void black and white"),
    ("a crown floating above empty space",    "a single playing card dissolving into moths",         "royal purple"),
    ("a jellyfish the size of a building",    "a tiny ship in a bottle navigating its tendrils",     "deep sea bioluminescent"),
    ("a spiral staircase with no structure",  "an hourglass where sand flows upward",                "marble and gold"),
    ("a telephone ringing in an empty field", "a rotary dial phone wrapped in vines",                "verdant green"),
    ("a mirror reflecting a different world", "a hand reaching through cracked glass",               "mercury silver"),
    ("a river flowing upward on the wall",    "a fish skeleton made of crystal",                     "sapphire blue"),
    ("an absent chess player mid-move",       "a single chess piece made of black obsidian",         "alabaster and jet"),
    ("a volcano made of ice",                 "a flame that casts a shadow of water",                "glacial fire"),
    ("a city seen from underwater",           "a submarine periscope emerging from dry land",        "submarine green"),
    ("a funeral for the sun",                 "a single black candle burning upward light",          "mourning violet"),
    ("a typewriter writing on its own",       "a letter sealed with wax dripping upward",            "ink and rust"),
]

ENVIRONMENTS = [
    "on a concrete surface, dramatic studio lighting from the left",
    "on polished obsidian, single overhead spotlight",
    "on weathered marble, soft diffused gallery light",
    "on cracked desert earth, harsh noon sun from above",
    "on wet stone, cold blue moonlight",
    "on aged wood, warm amber candlelight from the right",
    "on frosted glass surface, backlit with cold white light",
    "on matte black surface, twin spotlights creating double shadows",
    "on brushed steel, fluorescent clinical lighting",
    "on ancient parchment texture, golden hour side light",
]

DROPLET_STYLES = [
    "covered in photorealistic water droplets with light refraction",
    "beaded with mercury-like spherical droplets",
    "dripping with crystalline dew, each drop a perfect lens",
    "coated in condensation, micro-droplets catching the light",
    "wrapped in a thin film of water with large rolling drops",
]

THEMES = [
    "Transdifferentiation", "Liquid Mathematics", "Cosmic Regeneration",
    "Impossible Geometry",  "Neural Bioluminescence", "Temporal Dissolution",
    "Void Crystallization",  "Recursive Consciousness", "Phantom Cartography",
    "Entropic Memory",       "Spectral Architecture",   "Dissolved Identity",
]

# New: genuine Surrealist juxtaposition — unrelated objects in impossible encounter
IMPOSSIBLE_JUXTAPOSITIONS = [
    "a sewing machine entangled with the tentacles of a deep-sea anglerfish",
    "a rotary telephone growing out of a beehive",
    "an umbrella sprouting living coral instead of ribs",
    "a typewriter fused to the inside of a grand piano",
    "a pair of scissors embedded in a slice of frozen ocean",
    "a violin filled with swarming moths instead of strings",
    "a birdcage containing a single beating human heart",
    "a wheelchair made entirely of melting wax candles",
    "a chandelier dripping with living bees instead of crystal",
    "a microscope examining a miniature thunderstorm",
    "a wedding dress made of torn newspaper pages",
    "a stethoscope listening to the heartbeat of a stone",
]

# New: dream-logic temporal/spatial impossibility
DREAM_LOGIC_MODIFIERS = [
    "as if caught mid-dissolve between two separate moments in time",
    "simultaneously above and beneath the horizon line",
    "casting a shadow that appears to arrive before the object does",
    "frozen in a gesture that has no beginning or end",
    "existing in two places in the frame at once",
    "as though gravity in this corner of the scene points sideways",
    "appearing and disappearing at the edges like a half-remembered dream",
    "rendered with the logic of déjà vu, familiar yet wrong",
    "as if recalled from a memory that was never actually lived",
    "suspended in a moment that refuses to resolve into before or after",
]

# New: scale distortion, a classic surrealist destabilizer
SCALE_DISTORTIONS = [
    "small enough to fit inside a matchbox",
    "towering taller than the cathedral spire it has replaced",
    "the exact size of a single human eyelash",
    "vast enough to eclipse the horizon behind it",
    "shrinking and growing in the same frame, never settling on one size",
    "no larger than a grain of salt yet impossibly detailed",
    "filling the entire sky like a second, smaller sun",
    "scaled as if viewed simultaneously through a telescope and a microscope",
]

def build_prompt(token_id, complexity):
    # Local RNG instance per token — independent sampling instead of
    # modulo indexing, so combinations don't cycle every len(list) tokens
    rng = random.Random(token_id * 7331 + complexity)

    shadow_desc, subject_desc, color_desc = rng.choice(PHANTOM_SHADOWS)
    env           = rng.choice(ENVIRONMENTS)
    droplets      = rng.choice(DROPLET_STYLES)
    theme         = rng.choice(THEMES)
    juxtaposition = rng.choice(IMPOSSIBLE_JUXTAPOSITIONS)
    dream_mod     = rng.choice(DREAM_LOGIC_MODIFIERS)
    scale_mod     = rng.choice(SCALE_DISTORTIONS)

    prompt = (
        f"Surrealist fine art photography, hyperrealistic. "
        f"Completely monochromatic grayscale background and environment, "
        f"{env}. "
        f"The shadow of {shadow_desc} cast dramatically on the background wall, "
        f"but the object casting it is absent — only the shadow exists, "
        f"large and perfectly defined, {dream_mod}. "
        f"Elsewhere in frame, {juxtaposition} — an unrelated and impossible encounter. "
        f"In the foreground, {subject_desc}, {scale_mod}, {droplets}, "
        f"rendered in vivid {color_desc} — the ONLY color in the entire image. "
        f"Photorealistic studio photography, 8k detail, sharp focus, "
        f"soft bokeh background, Magritte, Dalí, and Gregory Crewdson aesthetic, "
        f"collector NFT art, masterpiece quality."
    )

    negative = (
        "cartoon, anime, painting, illustration, low quality, blurry, "
        "multiple colors in background, colorful background, busy, cluttered, "
        "text, watermark, signature, frame, border, ugly, deformed, "
        "multiple subjects, abstract blobs, primitive shapes"
    )

    concept = (shadow_desc, subject_desc, color_desc)
    return prompt, negative, theme, concept, juxtaposition, dream_mod, scale_mod

# ── MODEL LOADER ────────────────────────────────────────────────
_pipe = None

def load_pipeline():
    global _pipe
    if _pipe is not None:
        return _pipe

    print("\n🔧 Loading Stable Diffusion pipeline (first run downloads ~1.5GB)...")
    print("   This only happens once — model cached after first download.\n")

    from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

    model_id = "runwayml/stable-diffusion-v1-5"

    _pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.float32,   # float32 required on ARM CPU
        safety_checker=None,
        requires_safety_checker=False,
    )

    _pipe.scheduler = DPMSolverMultistepScheduler.from_config(_pipe.scheduler.config)
    _pipe = _pipe.to(DEVICE)

    # Memory optimizations for Android
    _pipe.enable_attention_slicing(1)
    _pipe.enable_vae_slicing()

    print("✅ Pipeline ready.\n")
    return _pipe

# ── POST-PROCESSING ──────────────────────────────────────────────
def post_process(img, complexity, accent_color_desc):
    img = ImageEnhance.Contrast(img).enhance(1.6 + complexity * 0.1)
    img = ImageEnhance.Brightness(img).enhance(0.95)
    img = ImageEnhance.Color(img).enhance(2.2 + complexity * 0.15)
    img = img.filter(ImageFilter.SHARPEN)
    img = img.filter(ImageFilter.SHARPEN)

    vignette = Image.new("L", (WIDTH, HEIGHT), 0)
    v_draw   = ImageDraw.Draw(vignette)
    for i in range(min(WIDTH, HEIGHT) // 2, 0, -4):
        darkness = int(255 * (1 - (i / (min(WIDTH, HEIGHT) / 2)) ** 1.5))
        v_draw.ellipse(
            [WIDTH//2 - i, HEIGHT//2 - i, WIDTH//2 + i, HEIGHT//2 + i],
            fill=darkness
        )
    vignette   = vignette.filter(ImageFilter.GaussianBlur(40))
    vignette_rgb = Image.merge("RGB", [vignette, vignette, vignette])
    img = ImageChops.multiply(img, vignette_rgb)
    img = ImageEnhance.Brightness(img).enhance(1.35)

    return img

# ── WATERMARK ───────────────────────────────────────────────────
def add_watermark(img, token_id, rarity):
    draw = ImageDraw.Draw(img)
    draw.text(
        (28, HEIGHT - 52),
        f"Thomas Lee Harvey  ·  #{token_id:04d}  ·  {rarity}",
        fill=(200, 210, 220),
        font=None
    )
    draw.text(
        (WIDTH - 220, 22),
        "ECHOES OF ETERNITY",
        fill=(180, 190, 200),
        font=None
    )
    return img

# ── GENERATION ──────────────────────────────────────────────────
def generate_nft(token_id):
    rarity, complexity = get_rarity(token_id)
    prompt, negative, theme, concept, juxtaposition, dream_mod, scale_mod = build_prompt(token_id, complexity)
    shadow_desc, subject_desc, color_desc = concept

    pipe = load_pipeline()

    steps = {1: 20, 2: 25, 3: 30, 4: 35, 5: 40}[complexity]
    guidance = 8.5 + (complexity * 0.5)

    generator = torch.Generator(device=DEVICE).manual_seed(token_id * 137 + complexity)

    result = pipe(
        prompt=prompt,
        negative_prompt=negative,
        width=WIDTH,
        height=HEIGHT,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=generator,
    )

    img = result.images[0]
    img = post_process(img, complexity, color_desc)
    img = add_watermark(img, token_id, rarity)

    return img, rarity, theme, subject_desc, shadow_desc, color_desc, juxtaposition, dream_mod, scale_mod

# ── METADATA BUILDER ─────────────────────────────────────────────
def build_metadata(token_id, rarity, theme, subject_desc, shadow_desc, color_desc,
                    juxtaposition, dream_mod, scale_mod):
    palette_name = ["Abyss Monochrome", "Dreamfire Void", "BioLume Dark",
                    "VoidBloom", "GoldenVoid"][token_id % 5]
    return {
        "name":        f"Echoes of Eternity: Jellyfish Dreams #{token_id:04d}",
        "description": (
            f"A surrealist NFT by Thomas Lee Harvey. The shadow of {shadow_desc} "
            f"dominates a monochrome world, cast by something absent. "
            f"The only color belongs to {subject_desc}. "
            f"Elsewhere, {juxtaposition}. "
            f"{rarity} tier."
        ),
        "image":       f"ipfs://YOUR_CID/images/{token_id:04d}.png",
        "edition":     token_id,
        "rarity":      rarity,
        "attributes": [
            {"trait_type": "Rarity",          "value": rarity},
            {"trait_type": "Creator",         "value": "Thomas Lee Harvey"},
            {"trait_type": "Style",           "value": "Surreal Abstract Realism"},
            {"trait_type": "Theme",           "value": theme},
            {"trait_type": "Phantom Shadow",  "value": shadow_desc},
            {"trait_type": "Color Subject",   "value": subject_desc[:40]},
            {"trait_type": "Accent Color",    "value": color_desc},
            {"trait_type": "Juxtaposition",   "value": juxtaposition[:40]},
            {"trait_type": "Dream Logic",     "value": dream_mod[:40]},
            {"trait_type": "Scale Distortion","value": scale_mod[:40]},
            {"trait_type": "Palette",         "value": palette_name},
            {"trait_type": "Collection",      "value": "Echoes of Eternity"},
        ]
    }

# ── MAIN LOOP ────────────────────────────────────────────────────
def main():
    print("🚀 Echoes of Eternity: Jellyfish Dreams — SD Generation")
    print(f"   Generating {TOTAL_NFTS} NFTs → {OUTPUT_DIR}\n")

    existing = set()
    for f in os.listdir(IMAGES_DIR):
        if f.endswith(".png"):
            try: existing.add(int(f.replace(".png","")))
            except: pass

    if existing:
        print(f"   ↩️  Resuming — {len(existing)} already generated, skipping.\n")

    start_time = time.time()

    for i in range(1, TOTAL_NFTS + 1):
        if i in existing:
            continue

        t0 = time.time()

        try:
            img, rarity, theme, subject, shadow, color, juxt, dream_mod, scale_mod = generate_nft(i)
        except Exception as e:
            print(f"❌ #{i:04d} failed: {e}")
            continue

        filename = f"{i:04d}"
        img.save(f"{IMAGES_DIR}/{filename}.png", optimize=True)

        meta = build_metadata(i, rarity, theme, subject, shadow, color, juxt, dream_mod, scale_mod)
        with open(f"{METADATA_DIR}/{filename}.json", "w") as f:
            json.dump(meta, f, indent=2)

        elapsed   = time.time() - t0
        total_e   = time.time() - start_time
        remaining = (total_e / i) * (TOTAL_NFTS - i)
        hrs, rem  = divmod(int(remaining), 3600)
        mins      = rem // 60

        if i % 10 == 0 or rarity in ["Black Diamond", "Super Rare"] or i <= 3:
            print(
                f"✅ #{i:04d} | {rarity:<14} | {elapsed:5.1f}s | "
                f"ETA {hrs}h {mins}m | {shadow[:35]}..."
            )

    print(f"\n🎉 Complete! {TOTAL_NFTS} NFTs saved to {OUTPUT_DIR}")
    print("   Open Photos app → Albums → Echoes_of_Eternity")

if __name__ == "__main__":
    main()
