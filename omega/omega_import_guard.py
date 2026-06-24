import sys
import importlib
import os

FORBIDDEN_SHADOWS = {
    "copy",
    "json",
    "sqlite3",
    "datetime",
    "telegram",
}

def enforce_import_safety():
    cwd = os.getcwd()

    for name in list(sys.modules.keys()):
        module = sys.modules[name]
        path = getattr(module, "__file__", "")

        if name in FORBIDDEN_SHADOWS and path and cwd in path:
            raise RuntimeError(
                f"IMPORT SHADOW DETECTED: {name} overridden by {path}"
            )

def safe_import(name: str):
    enforce_import_safety()
    return importlib.import_module(name)
