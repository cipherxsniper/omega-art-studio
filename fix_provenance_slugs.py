PATH = "/data/data/com.termux/files/home/omega_provenance_api.py"
with open(PATH) as f:
    src = f.read()

OLD = "def lookup_token(collection, token_id):"

NEW = """SLUG_MAP = {
    "echoes": "Echoes of Eternity",
    "somnium": "Somnium",
    "paracosm": "Paracosm",
    "monolith": "Monolith",
}

def lookup_token(collection, token_id):
    collection = SLUG_MAP.get(collection.lower(), collection)"""

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    with open(PATH, "w") as f:
        f.write(src)
    print("Fixed")
else:
    print("NOT FOUND")
