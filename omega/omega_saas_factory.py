import os
import time
import hashlib
import subprocess
import requests
from pathlib import Path
from datetime import datetime

ROOT = os.path.expanduser("~/Omega-Production")

STATE_FILE = os.path.expanduser("~/saas_state.db")

GITHUB_USER = "cipherxsniper"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # must be set in .env

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("OMEGA_CHAT_ID")

IGNORE = {".git", "__pycache__", ".pyc"}


# -----------------------------
# TELEGRAM
# -----------------------------
def telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        pass


# -----------------------------
# SCAN
# -----------------------------
def scan():
    files = []
    for p in Path(ROOT).rglob("*"):
        if not p.is_file():
            continue
        if any(i in str(p) for i in IGNORE):
            continue
        files.append(str(p))
    return files


# -----------------------------
# SAAS DETECTION (STRICT RULE)
# -----------------------------
def detect_saas(files):
    has_app = any("app.py" in f or "main.py" in f for f in files)
    has_req = any("requirements.txt" in f for f in files)
    has_backend = any("backend" in f for f in files)

    return has_app and has_req and has_backend


# -----------------------------
# EXTRACT PROJECT ROOT
# -----------------------------
def find_project_root(files):
    # naive: pick highest folder containing app.py
    for f in files:
        if "app.py" in f or "main.py" in f:
            return str(Path(f).parent)
    return None


# -----------------------------
# CREATE GITHUB REPO
# -----------------------------
def create_github_repo(name):
    url = "https://api.github.com/user/repos"

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}"
    }

    data = {
        "name": name,
        "private": False
    }

    r = requests.post(url, json=data, headers=headers)
    return r.status_code in [200, 201]


# -----------------------------
# PUSH PROJECT
# -----------------------------
def push_repo(path):
    try:
        subprocess.run(["git", "init"], cwd=path)
        subprocess.run(["git", "add", "."], cwd=path)
        subprocess.run(["git", "commit", "-m", "saas factory deploy"], cwd=path)
        subprocess.run(["git", "branch", "-M", "main"], cwd=path)

        subprocess.run([
            "git", "remote", "add", "origin",
            f"https://github.com/{GITHUB_USER}/{Path(path).name}.git"
        ], cwd=path)

        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=path)

        return True
    except:
        return False


# -----------------------------
# APPROVAL GATE STATE
# -----------------------------
pending = None


def request_approval(project):
    global pending
    pending = project

    telegram(
        f"""🚨 SAAS DETECTED

Project: {project}

Approve deployment:
/approve {project}
/reject {project}"""
    )


# -----------------------------
# APPROVAL CHECK (SIMPLIFIED)
# -----------------------------
def check_approval():
    # in real system: Telegram bot handles this
    # here we simulate approval via file flag
    return os.path.exists(f"{pending}.approved") if pending else False


# -----------------------------
# LOOP
# -----------------------------
def run():
    telegram("🧠 OMEGA SAAS FACTORY ONLINE")

    seen = set()

    while True:
        try:
            files = scan()

            if detect_saas(files):
                project = find_project_root(files)

                if project and project not in seen:
                    request_approval(project)
                    seen.add(project)

            # approval check
            if pending and check_approval():
                name = Path(pending).name

                ok = create_github_repo(name)
                if ok:
                    push_repo(pending)
                    telegram(f"🚀 DEPLOYED: {name}")

        except Exception as e:
            telegram(f"❌ ERROR: {e}")

        time.sleep(300)


if __name__ == "__main__":
    run()
