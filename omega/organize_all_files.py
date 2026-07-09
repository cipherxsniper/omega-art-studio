#!/usr/bin/env python3

import os
import shutil
from pathlib import Path

HOME = str(Path.home())

ROOT_SCAN_PATHS = [
    HOME
]

IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".cache",
    ".npm",
    ".cargo",
    ".gradle",
    ".local",
    ".config",
    ".termux",
    ".android",
    "storage",
}

CATEGORY_MAP = {
    "Archives": {
        ".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar"
    },
    "Documents": {
        ".pdf", ".doc", ".docx", ".txt", ".rtf",
        ".odt", ".csv", ".xlsx", ".xls",
        ".ppt", ".pptx", ".md", ".json",
        ".yaml", ".yml", ".xml"
    },
    "Images": {
        ".jpg", ".jpeg", ".png", ".gif",
        ".bmp", ".webp", ".svg", ".heic"
    },
    "Videos": {
        ".mp4", ".mkv", ".avi", ".mov",
        ".wmv", ".flv", ".webm", ".m4v"
    },
    "Audio": {
        ".mp3", ".wav", ".aac",
        ".ogg", ".flac", ".m4a"
    },
    "Code": {
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".java", ".c", ".cpp", ".h", ".hpp",
        ".sh", ".go", ".rs", ".php",
        ".rb", ".swift", ".kt", ".sql"
    },
    "Android": {
        ".apk", ".aab"
    }
}

ORGANIZED_ROOT = os.path.join(HOME, "Organized_Files")


def category_for_file(filename):
    ext = Path(filename).suffix.lower()

    for category, extensions in CATEGORY_MAP.items():
        if ext in extensions:
            return category

    return "Other"


def safe_name(path):
    if not os.path.exists(path):
        return path

    base = Path(path).stem
    ext = Path(path).suffix
    parent = str(Path(path).parent)

    counter = 1

    while True:
        candidate = os.path.join(
            parent,
            f"{base}_{counter}{ext}"
        )

        if not os.path.exists(candidate):
            return candidate

        counter += 1


def should_skip(path):
    parts = Path(path).parts

    for part in parts:
        if part in IGNORE_DIRS:
            return True

    if ORGANIZED_ROOT in str(path):
        return True

    return False


def move_file(src):
    category = category_for_file(src)

    destination_dir = os.path.join(
        ORGANIZED_ROOT,
        category
    )

    os.makedirs(destination_dir, exist_ok=True)

    filename = os.path.basename(src)

    first_letter = filename[:1].upper()

    if not first_letter.isalpha():
        first_letter = "0-9"

    destination_dir = os.path.join(
        destination_dir,
        first_letter
    )

    os.makedirs(destination_dir, exist_ok=True)

    destination = os.path.join(
        destination_dir,
        filename
    )

    destination = safe_name(destination)

    try:
        shutil.move(src, destination)
        print(f"MOVED: {src}")
    except Exception as e:
        print(f"SKIPPED: {src} -> {e}")


def organize():
    os.makedirs(ORGANIZED_ROOT, exist_ok=True)

    files = []

    for root_path in ROOT_SCAN_PATHS:

        for root, dirs, filenames in os.walk(root_path):

            dirs[:] = [
                d for d in dirs
                if d not in IGNORE_DIRS
            ]

            if should_skip(root):
                continue

            for filename in filenames:

                full_path = os.path.join(
                    root,
                    filename
                )

                if should_skip(full_path):
                    continue

                if os.path.isfile(full_path):
                    files.append(full_path)

    files.sort(
        key=lambda x: os.path.basename(x).lower()
    )

    total = len(files)

    print(f"\nFOUND {total} FILES\n")

    for file_path in files:
        move_file(file_path)

    print("\nORGANIZATION COMPLETE")
    print(f"OUTPUT DIRECTORY: {ORGANIZED_ROOT}")


if __name__ == "__main__":
    organize()
