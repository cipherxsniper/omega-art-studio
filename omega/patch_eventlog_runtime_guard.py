from pathlib import Path

file = Path("core/event_bus.py")
text = file.read_text()

if "if self.db is None" not in text:
    text += """

    def safe_write(self, event):
        if self.db is None:
            return None
        return self.db.insert(event)
"""

file.write_text(text)

print("[OK] event_bus runtime guard added")
