PATH = "/data/data/com.termux/files/home/omega_provenance_api.py"
with open(PATH) as f:
    src = f.read()

# Fix the padding logic to use token_id directly for filename
OLD = '''    meta_path = HOME / col["dir"] / "metadata" / f"{token_id:04d}.json"
    if not meta_path.exists():
        return jsonify({"error": "Metadata not found"}), 404'''

NEW = '''    meta_path = HOME / col["dir"] / "metadata" / f"{token_id}.json"
    if not meta_path.exists():
        meta_path = HOME / col["dir"] / "metadata" / f"{token_id:04d}.json"
    if not meta_path.exists():
        return jsonify({"error": "Metadata not found"}), 404'''

OLD2 = '''    img_path = HOME / col["dir"] / "images" / f"{token_id:04d}.png"'''
NEW2 = '''    img_path = HOME / col["dir"] / "images" / f"{token_id}.png"
    if not img_path.exists():
        img_path = HOME / col["dir"] / "images" / f"{token_id:04d}.png"'''

src = src.replace(OLD, NEW, 1).replace(OLD2, NEW2, 1)
with open(PATH, "w") as f:
    f.write(src)
print("Fixed")
