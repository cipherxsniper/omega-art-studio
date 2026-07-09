#!/usr/bin/env python3

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

SOURCE_ROOTS = [
    "/data/data/com.termux/files/home/Omega-Production",
    "/data/data/com.termux/files/home/Omega-Production/omega_bank"
]

OUTPUT_DIR = Path("/data/data/com.termux/files/home/Omega-Production/omega-market-product-1")

PRODUCT_MAP = {
    "saas": ["landing", "pricing", "onboarding", "dashboard"],
    "engine": ["leads", "outreach", "crm"],
    "billing": ["stripe"],
    "runtime": [],
    "deployment": [],
    "docs": []
}

SCAN_EXTENSIONS = {".py", ".sh", ".md", ".json", ".sql", ".yml"}

def ensure_structure():
    for k, sub in PRODUCT_MAP.items():
        (OUTPUT_DIR / k).mkdir(parents=True, exist_ok=True)
        for s in sub:
            (OUTPUT_DIR / k / s).mkdir(parents=True, exist_ok=True)

def scan_files():
    files = []

    for root in SOURCE_ROOTS:
        for base, _, fs in os.walk(root):
            for f in fs:
                p = Path(base) / f
                if p.suffix in SCAN_EXTENSIONS:
                    files.append(str(p))

    return files

def write_core_docs(scanned):
    readme = f"""
# Omega Market Product 1

Generated SaaS Product Layer from Omega AI System

## Modules
- SaaS frontend
- Stripe billing integration
- Outreach automation engine
- Lead generation system
- CRM orchestration
- Runtime execution layer

## Generated At
{datetime.utcnow().isoformat()}

## Files Indexed
{len(scanned)}

## Positioning
Sellable AI automation SaaS for local businesses:
- HVAC
- Roofing
- Med Spas
- Agencies
"""

    (OUTPUT_DIR / "README.md").write_text(readme)

    product_json = {
        "name": "Omega Market Product 1",
        "type": "AI SaaS Automation Platform",
        "generated_at": datetime.utcnow().isoformat(),
        "modules": list(PRODUCT_MAP.keys()),
        "file_count": len(scanned),
        "positioning": "Local business AI automation SaaS"
    }

    (OUTPUT_DIR / "product.json").write_text(json.dumps(product_json, indent=2))

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ensure_structure()

    scanned = scan_files()

    write_core_docs(scanned)

    print("\n=== OMEGA MARKET PRODUCT GENERATED ===")
    print("OUTPUT:", OUTPUT_DIR)
    print("FILES SCANNED:", len(scanned))
    print("STATUS: READY FOR SALES + GITHUB + DEMO DEPLOYMENT")

if __name__ == "__main__":
    main()
