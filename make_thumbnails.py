#!/usr/bin/env python3
from pathlib import Path
from PIL import Image

COLLECTIONS = ["echoes_of_eternity", "somnium", "paracosm", "monolith"]
THUMB_WIDTH = 360

total_before = total_after = count = 0

for name in COLLECTIONS:
    base = Path.home() / name
    src_dir, out_dir = base / "images", base / "thumbnails"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not src_dir.exists():
        print(f"  skip {name}: no images dir"); continue
    for f in sorted(src_dir.glob("*.png")):
        out_path = out_dir / (f.stem + ".jpg")
        if out_path.exists():
            continue
        try:
            img = Image.open(f).convert("RGB")
            w, h = img.size
            img = img.resize((THUMB_WIDTH, int(h * THUMB_WIDTH / w)), Image.LANCZOS)
            img.save(out_path, "JPEG", quality=80, optimize=True)
            total_before += f.stat().st_size
            total_after += out_path.stat().st_size
            count += 1
        except Exception as e:
            print(f"  ERROR {f.name}: {e}")
    print(f"  {name}: done")

print(f"\nGenerated {count} thumbnails")
if total_before:
    print(f"Before: {total_before/1024/1024:.1f}MB -> After: {total_after/1024/1024:.1f}MB ({100*total_after/total_before:.0f}%)")
