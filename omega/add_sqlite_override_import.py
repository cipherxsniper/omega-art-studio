#!/usr/bin/env python3
import sys
from pathlib import Path

IMPORT_LINE = "import omega_sqlite_override\n"

def patch_file(file_path):
    path = Path(file_path)

    if not path.exists():
        print("[SKIP] Not found:", file_path)
        return

    content = path.read_text()

    if "omega_sqlite_override" in content:
        print("[OK] Already patched:", file_path)
        return

    path.write_text(IMPORT_LINE + content)
    print("[PATCHED]", file_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_sqlite_override_import.py <file.py>")
        sys.exit(1)

    patch_file(sys.argv[1])
