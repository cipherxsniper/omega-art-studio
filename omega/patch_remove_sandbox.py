path = "/data/data/com.termux/files/home/omega_v10.py"
content = open(path).read()

old = '''        "🏛 *TREASURY RESERVES*\\n"
        f"  Primary Treasury:  {primary_bal}\\n"
        f"  Sandbox Reserve:   {sandbox_bal}\\n"'''

new = '''        "🏛 *TREASURY RESERVES*\\n"
        f"  OMEGA_MAIN_RESERVE: {primary_bal}\\n"'''

assert old in content, "anchor not found"
content = content.replace(old, new)
open(path, "w").write(content)
print("Sandbox removed")
