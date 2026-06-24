from pathlib import Path

file = Path("core/event_bus.py")
text = file.read_text()

# remove top-level import if present
text = text.replace("from core.event_queue import", "# from core.event_queue import (lazy import applied)\n# from core.event_queue import")

# inject lazy import safety wrapper if missing
if "def get_queue" not in text:
    text += """

def get_queue():
    from core.event_queue import EventQueue
    return EventQueue()
"""

file.write_text(text)

print("[OK] event_bus circular import patched (lazy import applied)")
