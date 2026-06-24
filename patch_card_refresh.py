path = "/data/data/com.termux/files/home/omega_v10.py"
content = open(path).read()

old = '''            text = (
                "💳 *OMEGA VIRTUAL CARDS*\\n"
                "━━━━━━━━━━━━━━━━━━━━━━\\n"
                f"  Total: {len(cards)} card(s)\\n"
                "━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
                + "\\n\\n".join(lines)
            )'''

new = '''            from datetime import datetime as _dt
            _now = _dt.now().strftime("%H:%M:%S")
            text = (
                f"💳 *OMEGA VIRTUAL CARDS* — {_now}\\n"
                "━━━━━━━━━━━━━━━━━━━━━━\\n"
                f"  Total: {len(cards)} card(s)\\n"
                "━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
                + "\\n\\n".join(lines)
            )'''

assert old in content, "anchor not found"
content = content.replace(old, new)
open(path, "w").write(content)
print("Card refresh fixed")
