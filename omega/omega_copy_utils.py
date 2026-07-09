#!/usr/bin/env python3

import os
import sys

out_file = "omega_dump.txt"

files = [f for f in os.listdir(".") if os.path.isfile(f)]

with open(out_file, "w") as out:

    out.write("OMEGA DIRECTORY DUMP\n")
    out.write("====================\n\n")

    for f in files:
        try:
            with open(f, "r") as src:
                content = src.read()

            out.write(f"\n\n===== {f} =====\n\n")
            out.write(content)

        except Exception as e:
            out.write(f"\n\n===== {f} (SKIPPED: {e}) =====\n")

print("[DUMP CREATED]", out_file)
