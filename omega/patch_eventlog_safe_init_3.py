from pathlib import Path

file = Path("core/event_bus.py")
text = file.read_text()

# fix unsafe instantiation pattern
text = text.replace(
    "EventLog()",
    "EventLog(db=None)"
)

# make constructor safe if db is missing
if "def __init__(self, db" in text:
    text = text.replace(
        "def __init__(self, db",
        "def __init__(self, db=None"
    )

# guard db usage safely
if "self.db = db" in text:
    text = text.replace(
        "self.db = db",
        "self.db = db or None"
    )

file.write_text(text)

print("[OK] EventLog made safe for bootstrap runtime")
