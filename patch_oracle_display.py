path = "/data/data/com.termux/files/home/omega_oracle_v2.py"
content = open(path).read()

old = '''        print(f"  Delta: {'+' if entry['delta'] >= 0 else ''}{entry['delta']} pts  |  Best ever: {best_ever}/100")'''

new = '''        percentile = entry.get("percentile", 100.0)
        violations = entry.get("floor_violations", [])
        print(f"  Delta: {'+' if entry['delta'] >= 0 else ''}{entry['delta']} pts  |  Best ever: {best_ever}/100  |  Percentile: {percentile}%")
        if violations:
            print(f"  🚨 RATCHET VIOLATIONS:")
            for v in violations:
                print(f"     {v}")'''

assert old in content, "anchor not found"
content = content.replace(old, new)
open(path, "w").write(content)
print("Display updated")
