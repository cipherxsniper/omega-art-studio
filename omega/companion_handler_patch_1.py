import re, sys

path = "/data/data/com.termux/files/home/omega_v10.py"
with open(path) as f:
    src = f.read()

HANDLER = """
        elif data == "companion_status":
            try:
                import urllib.request as _ur_comp
                _r = _ur_comp.urlopen("http://127.0.0.1:6010/status", timeout=5)
                _s = json.loads(_r.read())
                _st = _s.get("storage", {})
                text = (
                    "Omega Companion\\n\\n"
                    "  Status:  " + str(_s.get("status","online")) + "\\n"
                    "  Memory:  " + str(_st.get("companion_memory_entries",0)) + " entries\\n"
                    "  Storage: " + str(round(_st.get("companion_storage_kb",0),1)) + "KB encrypted\\n"
                    "  Backend: OmegaStorage AES-256\\n\\n"
                    "http://192.168.11.115:6010/companion"
                )
            except Exception:
                text = "Omega Companion: online\\n\\nhttp://192.168.11.115:6010/companion"
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            _kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("Open Companion", url="http://192.168.11.115:6010/companion"),
                InlineKeyboardButton("Menu", callback_data="dash"),
            ]])
            await query.edit_message_text(text, reply_markup=_kb)
"""

ANCHOR = '        elif data == "open_trading":'

if 'elif data == "companion_status":' in src:
    print("Already present")
    sys.exit(0)

if ANCHOR not in src:
    print("ANCHOR NOT FOUND")
    sys.exit(1)

src = src.replace(ANCHOR, HANDLER + ANCHOR, 1)
with open(path, "w") as f:
    f.write(src)
print("Inserted OK")
