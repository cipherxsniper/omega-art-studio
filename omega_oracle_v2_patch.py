"""
PATCH: Add omega_storage_watch to Oracle v2 scoring.
Add this to your omega_oracle_v2.py components list.
"""

# Add to your COMPONENTS dict in omega_oracle_v2.py:
# "omega_storage": {"weight": 0.05, "score": 0, "max": 100}

# Add this function and call it in your main() scoring loop:

def score_storage():
    """Run storage watch and return score."""
    import subprocess
    try:
        result = subprocess.run(
            ["python3", os.path.expanduser("~/omega_storage_watch.py")],
            capture_output=True, text=True, timeout=30
        )
        # Parse score from output
        for line in result.stdout.split("\n"):
            if "STORAGE SCORE:" in line:
                score_str = line.split(":")[1].split("/")[0].strip()
                return int(score_str)
        return 0
    except Exception as e:
        print(f"Storage watch failed: {e}")
        return 0

# In your main scoring loop, add:
# components["omega_storage"]["score"] = score_storage()
