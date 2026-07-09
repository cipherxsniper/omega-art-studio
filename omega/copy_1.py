#!/usr/bin/env python3
"""
copy.py — instant file printer for Termux
Usage:  python copy.py <filename>

Prints the entire file to stdout so you can scroll up and copy it,
OR pipes directly to Termux clipboard if termux-clipboard-set is available.
"""
import sys
import os
import shutil
import subprocess

def main():
    if len(sys.argv) < 2:
        print("Usage: python copy.py <filename>")
        sys.exit(1)

    path = sys.argv[1]

    if not os.path.exists(path):
        print(f"Error: '{path}' not found.")
        sys.exit(1)

    content = open(path, encoding="utf-8", errors="replace").read()

    # Try Termux clipboard first
    if shutil.which("termux-clipboard-set"):
        try:
            subprocess.run(
                ["termux-clipboard-set"],
                input=content,
                text=True,
                check=True,
            )
            lines = content.count("\n") + 1
            size  = len(content)
            print(f"✅ '{path}' copied to clipboard  ({lines} lines, {size} chars)")
            return
        except subprocess.CalledProcessError:
            pass  # fall through to stdout dump

    # Fallback: dump to stdout so you can scroll-select manually
    print(f"\n{'━'*60}")
    print(f"  FILE: {path}")
    print(f"{'━'*60}\n")
    print(content)
    print(f"\n{'━'*60}")
    print(f"  Scroll up to select and copy manually.")
    print(f"  (Install Termux:API + termux-clipboard-set for auto-copy)")
    print(f"{'━'*60}")

if __name__ == "__main__":
    main()
