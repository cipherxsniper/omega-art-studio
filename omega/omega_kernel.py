#!/usr/bin/env python3
"""
OMEGA RUNTIME KERNEL
All execution must pass through this layer
"""

import sys
import runpy
import omega_bootstrap  # ensures DB routing is active

print("[OMEGA KERNEL] Boot sequence initialized")

if len(sys.argv) < 2:
    print("Usage: python omega_kernel.py <script.py>")
    sys.exit(1)

script = sys.argv[1]

print(f"[OMEGA KERNEL] Launching controlled runtime: {script}")

runpy.run_path(script, run_name="__main__")
