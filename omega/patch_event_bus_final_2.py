from pathlib import Path

file = Path("core/event_bus.py")
text = file.read_text()

text = text.replace(
    "from core.queue import",
    "from core.event_queue import"
)

file.write_text(text)

print("[OK] event_bus updated to event_queue")
