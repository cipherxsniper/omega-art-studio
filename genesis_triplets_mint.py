#!/usr/bin/env python3
"""
GENESIS TRIPLETS MINT — Official Birth of Hypersurrealism
Pre-organized folder structure
"""

import sys, os, json, uuid, hashlib
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
sys.path.insert(0, str(HOME))

from dotenv import load_dotenv
load_dotenv(HOME / ".env")

try:
    from omega_om109 import generate_om109_fingerprint
    from omega_card_engine import _card_chain_hash
except ImportError:
    def generate_om109_fingerprint(data): 
        return hashlib.sha256(f"OM109_{json.dumps(data, sort_keys=True)}".encode()).hexdigest()
    _LAST_CARD_HASH = "GENESIS"
    def _card_chain_hash(event, prev): 
        return hashlib.sha256(f"{prev}{json.dumps(event, sort_keys=True)}".encode()).hexdigest()[:32]

BASE_DIR = HOME / "hypersurrealism/genesis_triplets"

def mint_triplet(image_filename, title, description, number):
    image_path = BASE_DIR / "images" / image_filename
    if not image_path.exists():
        print(f"❌ Missing: {image_path}")
        print(f"   Save your generated image as {image_filename} in {BASE_DIR}/images/")
        return None

    image_hash = hashlib.sha256(image_path.read_bytes()).hexdigest()
    timestamp = datetime.now(timezone.utc).isoformat()

    metadata = {
        "title": title,
        "description": description,
        "artist": "Thomas Lee Harvey",
        "movement": "Hypersurrealism",
        "series": "Genesis Triplets",
        "number": number,
        "image_hash": image_hash,
        "timestamp": timestamp,
        "academia_provenance": "https://www.academia.edu/ThomasLeeHarvey/Hypersurrealism",
        "rarity": "BLACK_DIAMOND",
        "edition": "1/1"
    }

    om109_fingerprint = generate_om109_fingerprint(metadata)
    nft_token = f"hs_genesis_{number}_{uuid.uuid4().hex[:12]}"

    ledger_event = {
        "nft_token": nft_token,
        "title": title,
        "owner": "Thomas Lee Harvey",
        "om109_coa": om109_fingerprint,
        "image_hash": image_hash,
        "rarity": "BLACK_DIAMOND",
        "timestamp": timestamp,
        "type": "GENESIS_TRIPLET"
    }

    global _LAST_CARD_HASH
    chain_hash = _card_chain_hash(ledger_event, getattr(sys.modules[__name__], '_LAST_CARD_HASH', "GENESIS"))
    _LAST_CARD_HASH = chain_hash

    record = {
        "nft_token": nft_token,
        "title": title,
        "rarity": "BLACK_DIAMOND",
        "om109_coa": om109_fingerprint,
        "image_hash": image_hash,
        "chain_hash": chain_hash,
        "metadata": metadata,
        "minted_at": timestamp,
        "status": "IMMUTABLE"
    }

    # Save metadata
    meta_path = BASE_DIR / "metadata" / f"genesis_{number}.json"
    meta_path.write_text(json.dumps(record, indent=2))

    print(f"🎉 GENESIS TRIPLET #{number} MINTED — {nft_token}")
    print(f"OM109 COA: {om109_fingerprint[:32]}...")
    print(f"Metadata saved to {meta_path}")
    return record

if __name__ == "__main__":
    print("🚀 Minting Genesis Triplets — Birth of Hypersurrealism\n")
    mint_triplet("hs_genesis_001.png", "Teal Apple Breaking Reality", "The Origin Piece", 1)
    mint_triplet("hs_genesis_002.png", "Upside-Down Mountain with Flowing Sky River", "Impossible Gravity", 2)
    mint_triplet("hs_genesis_003.png", "Burning Match with Water Crawling Upward", "Defiance of Physics", 3)
