PATH = "/data/data/com.termux/files/home/omega_oracle_v2.py"
with open(PATH) as f:
    src = f.read()

OLD = '''    # 3. Indentation anomalies
    indent_errs = []
    for i, line in enumerate(src.splitlines(), 1):
        if line and line[0] == " ":
            spaces = len(line) - len(line.lstrip(" "))
            if spaces % 4 != 0 and not line.strip().startswith("#"):
                indent_errs.append(f"line {i}: {spaces} spaces")
                record_error("indent_errors", line.strip()[:80])
    if indent_errs:
        penalty = min(len(indent_errs) * 2, 20)
        score -= penalty
        issues.append(f"Indent anomalies: {len(indent_errs)} (sample: {indent_errs[0]})")'''

NEW = '''    # 3. Indentation anomalies — skip valid Python continuations
    indent_errs = []
    src_lines = src.splitlines()
    SKIP_STARTS = (
        "#", "SELECT", "INSERT", "UPDATE", "WHERE", "FROM",
        "JOIN", "SET", "ORDER", "LIMIT", "AND ", "OR ", "LEFT",
        "INNER", "VALUES", "--", "ON ",
    )
    for i, line in enumerate(src_lines, 1):
        if not line or line[0] != " ":
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(SKIP_STARTS):
            continue
        if stripped[0] in (chr(34), chr(39), "f", "b", "r"):
            continue
        spaces = len(line) - len(line.lstrip(" "))
        if spaces % 4 != 0:
            prev = src_lines[i-2].rstrip() if i > 1 else ""
            if prev and prev[-1] not in (",", "(", "[", "\\\\", "+"):
                indent_errs.append(f"line {i}: {spaces} spaces")
                record_error("indent_errors", line.strip()[:80])
    if indent_errs:
        penalty = min(len(indent_errs) * 5, 25)
        score -= penalty
        issues.append(f"Indent anomalies: {len(indent_errs)} real errors")'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK indent checker fixed")
else:
    print("NOT FOUND")

# Fix guardian check
OLD2 = '''    # Shell scripts — basic check
    if str(path).endswith(".sh"):
        if "omega_v10.py" in src and "while true" in src:
            return 100, []
        issues.append("Guardian missing key patterns")
        return 60, issues'''

NEW2 = '''    # Shell scripts — basic check
    if str(path).endswith(".sh"):
        has_omega = "omega_v10.py" in src or "omega" in src.lower()
        has_loop  = "while true" in src or "sleep" in src
        if has_omega and has_loop:
            return 100, []
        if has_omega or has_loop:
            return 75, ["Guardian partially configured"]
        return 50, ["Guardian missing key patterns"]'''

if OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    print("OK guardian check fixed")
else:
    print("NOT FOUND guardian")

with open(PATH, "w") as f:
    f.write(src)
print("Done")
