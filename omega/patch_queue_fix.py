from pathlib import Path

file = Path("core/queue.py")
text = file.read_text()

# hard remove unsafe import
text = text.replace("import core.event_bus", "# import core.event_bus (removed circular dependency)")

# safe optional hook pattern
if "def publish_event_bus" not in text:
    text += """

def publish_event_bus(event):
    # lazy import to avoid circular dependency
    from core.event_bus import EventBus
    bus = EventBus()
    return bus.publish("queue_event", event)
"""

file.write_text(text)

print("[OK] queue circular import patched")
