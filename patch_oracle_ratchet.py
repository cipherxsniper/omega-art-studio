path = "/data/data/com.termux/files/home/omega_oracle_v2.py"
content = open(path).read()

old = '''def save_history(entry: dict):
    history = load_history()
    history.append(entry)
    # Keep last 100 entries
    if len(history) > 100:
        history = history[-100:]
    HISTORY.write_text(json.dumps(history, indent=2))'''

new = '''def save_history(entry: dict):
    history = load_history()
    history.append(entry)
    if len(history) > 100:
        history = history[-100:]
    HISTORY.write_text(json.dumps(history, indent=2))

# ── Component floor registry — scores can never go below their best ──
FLOOR_FILE = HOME / "omega_oracle_floors.json"

def load_floors() -> dict:
    try:
        return json.loads(FLOOR_FILE.read_text())
    except:
        return {}

def update_floors(components: dict):
    floors = load_floors()
    updated = False
    for name, score in components.items():
        if score > floors.get(name, 0):
            floors[name] = score
            updated = True
    if updated:
        FLOOR_FILE.write_text(json.dumps(floors, indent=2))
    return floors

def check_floors(components: dict) -> list:
    """Returns violations where a component dropped below its floor."""
    floors = load_floors()
    violations = []
    # Only flag code regressions — skip DB components (infrastructure)
    infra = {"omega_bank_db", "omega_ledger_db"}
    for name, score in components.items():
        if name in infra:
            continue
        floor = floors.get(name, 0)
        if score < floor:
            violations.append(
                f"{name} dropped to {score} (floor: {floor}) — RATCHET VIOLATION"
            )
    return violations

def compute_percentile(history: list) -> float:
    """What percentile is the current score vs all history."""
    if len(history) < 2:
        return 100.0
    scores = [h.get("total", 0) for h in history]
    current = scores[-1]
    below = sum(1 for s in scores[:-1] if s <= current)
    return round((below / (len(scores) - 1)) * 100, 1)'''

assert old in content, "anchor not found"
content = content.replace(old, new)
open(path, "w").write(content)
print("Ratchet written")

# Part 2 — wire into run_score output
path = "/data/data/com.termux/files/home/omega_oracle_v2.py"
content = open(path).read()

old = '''    save_history(entry)
    return entry'''

new = '''    # Update component floors — ratchet forward
    update_floors(component_scores)

    # Check for ratchet violations
    violations = check_floors(component_scores)

    # Compute percentile rank
    all_history = load_history()
    percentile = compute_percentile(all_history)
    entry["percentile"] = percentile
    entry["floor_violations"] = violations

    save_history(entry)
    return entry'''

assert old in content, "anchor2 not found"
content = content.replace(old, new)
open(path, "w").write(content)
print("Ratchet wired into run_score")
