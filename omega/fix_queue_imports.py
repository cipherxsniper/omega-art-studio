from pathlib import Path

replacements = [
    ("from core.event_queue import", "from core.event_queue import"),
    ("import core.event_queue", "import core.event_queue"),
]

for path in Path(".").rglob("*.py"):
    try:
        text = path.read_text()
        original = text

        for a, b in replacements:
            text = text.replace(a, b)

        if text != original:
            path.write_text(text)
            print("[FIXED]", path)

    except Exception as e:
        print("[SKIP]", path, e)
