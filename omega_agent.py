#!/usr/bin/env python3
"""
omega_agent.py — Terminal-access agent loop (the "Manus companion" pattern)

The model proposes ONE action at a time as strict JSON. This controller
executes it, feeds the result back, repeats. The model never touches the
shell or filesystem directly — every action passes through here first.

Actions: bash | read_file | write_file | list_dir | query_db | score_oracle |
         propose_patch | http_get | run_playbook | web_fetch | web_search |
         git_op | http_request | plan | done

Safety:
- File ops restricted to ALLOWED_ROOT unless you deliberately widen it
- Destructive command patterns (rm -rf, mass mv/reorg, git reset --hard,
  dd, mkfs, fork bombs...) are blocked outright
- query_db is SELECT-only, enforced at the app layer (grammar doesn't and
  can't guarantee this — the regex check below is the real gate)
- http_get restricted to localhost only; http_request is deliberately open
  to any external URL (explicit choice) — this is a real trust boundary,
  not an oversight: anything this agent fetches, or is told to send, can
  reach the outside world. Treat prompts that could touch this action with
  the same care as the ledger itself.
- git_op only accepts commands starting with "git ", runs cwd-contained to
  ALLOWED_ROOT, still passes through the same BLOCKED_PATTERNS check (git
  reset --hard / git push --force already forbidden there). NOTE: this is
  cwd-containment, not airtight path sandboxing — an absolute path outside
  ALLOWED_ROOT in the command's own arguments is not blocked. Known
  limitation, not a false sense of security.
- Hard step limit per task, hard timeout per command
- Every action + result is logged to omega_agent_log.jsonl for audit

GRAMMAR NOTE: as of this version, json.gbnf uses a GENERIC shape (action
first, then any combination of known string fields) instead of one hardcoded
alternative per action. This means adding a new tool from here on only
requires a new `if kind == "..."` block below plus a system-prompt schema
line — NOT a grammar file edit. Previously, 5 actions (query_db, score_oracle,
propose_patch, http_get, run_playbook) were silently unreachable because the
old grammar only allowed 5 different shapes and none of them matched — the
model could never legally emit them. Confirmed fixed by this rewrite.
"""

import sys
import json
import re
import subprocess
import psycopg2
import urllib.request
import urllib.error
import urllib.parse
import http.cookiejar
from pathlib import Path
from datetime import datetime, timezone

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # web_search degrades to an explicit error if bs4 is missing

BRAIN_URL = "http://localhost:8095/generate"
ALLOWED_ROOT = Path.home() / "omega_workspace"  # widen deliberately, not by default
MAX_STEPS = 12
CMD_TIMEOUT = 30

# Must exceed omega_brain.py's own LLAMA_SERVER call timeout (90s) — otherwise
# this client always gives up before the brain could ever have responded,
# which looks exactly like a freeze followed by a silent failure.
BRAIN_TIMEOUT = 300

LOG_PATH = Path.home() / "omega_agent_log.jsonl"

BLOCKED_PATTERNS = [
    r"rm\s+-rf\s+/(\s|$)",
    r"rm\s+-rf\s+~(\s|$)",
    r"\bdd\s+if=",
    r"\bmkfs\b",
    r":\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:",   # fork bomb
    r"git\s+reset\s+--hard",
    r"git\s+push\s+--force",
    r"\bmv\b.*\*.*omega",                   # bulk moves touching omega files
    r"find\s+.*-delete",
    r"chmod\s+-R\s+777\s+/",
]

SYSTEM_PROMPT = """You are Omega's agent, operating with real terminal access on Thomas's Termux system.
You act ONE STEP AT A TIME. Respond with STRICT JSON ONLY — no prose outside the JSON object.

Schema (pick exactly one per response):
{"action": "bash", "command": "<shell command>", "reasoning": "<why>"}
{"action": "read_file", "path": "<path>", "reasoning": "<why>"}
{"action": "write_file", "path": "<path>", "content": "<content>", "reasoning": "<why>"}
{"action": "list_dir", "path": "<path>", "reasoning": "<why>"}
{"action": "query_db", "sql": "<SELECT-only query>", "reasoning": "<why>"}
{"action": "score_oracle", "reasoning": "<why>"}
{"action": "propose_patch", "path": "<path>", "content": "<patch content>", "reasoning": "<why>"}
{"action": "http_get", "url": "<http://127.0.0.1:PORT/path>", "reasoning": "<why>"}
{"action": "run_playbook", "name": "<one of the 8 allowed playbooks>", "reasoning": "<why>"}
{"action": "web_fetch", "url": "<any external URL>", "reasoning": "<why>"}
{"action": "web_search", "query": "<search terms>", "reasoning": "<why>"}
{"action": "git_op", "command": "<full command starting with 'git '>", "reasoning": "<why>"}
{"action": "http_request", "method": "<GET|POST|PUT|DELETE>", "url": "<any URL>", "headers": "<JSON string, optional>", "body": "<string, optional>", "reasoning": "<why>"}
{"action": "plan", "tasks": "<step one>|<step two>|<step three>", "reasoning": "<why>"}
{"action": "done", "summary": "<what was accomplished>"}

Rules:
- One action per response. Never chain multiple actions in one JSON object.
- Never attempt file reorganization or bulk moves across the Omega codebase — forbidden, no exceptions.
- Prefer read/list before you write or run anything destructive.
- query_db only accepts SELECT statements — anything else is rejected before it reaches the database.
- http_get only works for localhost/127.0.0.1 — use http_request for external APIs.
- git_op commands must start with literally "git " — no other binaries.
- Use "plan" once at the start of a multi-step task to lay out your steps, then work through them
  one action at a time in the following turns — plan does not execute anything by itself.
- If a command fails, read the error and adjust — don't repeat the same failing command twice.
- Call "done" as soon as the task is actually complete. Don't pad steps.
"""


def log_step(step):
    step["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(step) + "\n")
    # normalized trace line for the console frontend
    action = step.get("action", {}) if isinstance(step.get("action"), dict) else {}
    result = step.get("result") or {}
    trace = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "tool": action.get("action", "think"),
        "cmd": action.get("command") or action.get("path") or action.get("sql")
               or action.get("url") or action.get("query") or action.get("tasks")
               or action.get("reasoning", ""),
        "result": json.dumps(result)[:500],
        "ok": ("error" not in result) and (result.get("returncode", 0) == 0),
    }
    with open(Path.home() / "omega_agent_trace.jsonl", "a") as f:
        f.write(json.dumps(trace) + "\n")


def is_blocked(command):
    for pat in BLOCKED_PATTERNS:
        if re.search(pat, command):
            return pat
    return None


def call_brain(prompt, max_tokens=400):
    data = json.dumps({"prompt": prompt, "max_tokens": max_tokens, "grammar": True}).encode()
    req = urllib.request.Request(BRAIN_URL, data=data, headers={"Content-Type": "application/json"})
    print(f"[omega_agent] waiting on brain (up to {BRAIN_TIMEOUT}s — CPU inference is slow, this is not a hang)...", file=sys.stderr)
    try:
        with urllib.request.urlopen(req, timeout=BRAIN_TIMEOUT) as resp:
            return json.loads(resp.read())["response"]
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"brain returned HTTP {e.code}: {body}") from e


def parse_action(raw_text):
    start = raw_text.find("{")
    if start == -1:
        raise ValueError(f"no JSON object found in model output: {raw_text[:200]}")
    try:
        obj, _ = json.JSONDecoder().raw_decode(raw_text[start:])
        return obj
    except json.JSONDecodeError as e:
        raise ValueError(f"malformed JSON in model output: {e} | raw: {raw_text[:200]}")


def safe_path(path_str):
    p = Path(path_str)
    p = p.resolve() if p.is_absolute() else (ALLOWED_ROOT / path_str).resolve()
    root = ALLOWED_ROOT.resolve()
    if root not in p.parents and p != root:
        raise PermissionError(f"{p} is outside ALLOWED_ROOT ({root}) — widen explicitly if intentional")
    return p


def _strip_html(raw):
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def execute(action):
    kind = action.get("action")

    if kind == "bash":
        cmd = action.get("command", "")
        blocked = is_blocked(cmd)
        if blocked:
            return {"error": f"blocked: command matched forbidden pattern ({blocked})"}
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=CMD_TIMEOUT)
            return {"stdout": result.stdout[-4000:], "stderr": result.stderr[-2000:], "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            return {"error": f"command timed out after {CMD_TIMEOUT}s"}

    if kind == "read_file":
        try:
            p = safe_path(action["path"])
            return {"content": p.read_text()[-6000:]}
        except Exception as e:
            return {"error": str(e)}

    if kind == "write_file":
        try:
            p = safe_path(action["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(action.get("content", ""))
            return {"written": str(p), "bytes": len(action.get("content", ""))}
        except Exception as e:
            return {"error": str(e)}

    if kind == "list_dir":
        try:
            p = safe_path(action.get("path", "."))
            return {"entries": [x.name for x in p.iterdir()]}
        except Exception as e:
            return {"error": str(e)}

    if kind == "query_db":
        sql = action.get("sql", "").strip()
        if not re.match(r"(?is)^\s*select\b", sql):
            return {"error": "query_db only permits SELECT statements"}
        if ";" in sql.rstrip(";"):
            return {"error": "query_db rejects multi-statement input (semicolon detected mid-query)"}
        try:
            conn = psycopg2.connect(host="127.0.0.1", port=5544, dbname="omega_bank",
                                     user="u0_a321", connect_timeout=5)
            cur = conn.cursor()
            cur.execute(sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchmany(50)
            conn.close()
            return {"columns": cols, "rows": rows}
        except Exception as e:
            return {"error": str(e)}

    if kind == "score_oracle":
        try:
            result = subprocess.run(
                ["python3", str(Path.home() / "omega_oracle_v2.py")],
                capture_output=True, text=True, timeout=30,
            )
            return {"stdout": result.stdout[-3000:], "returncode": result.returncode}
        except Exception as e:
            return {"error": str(e)}

    if kind == "propose_patch":
        try:
            p = safe_path(action["path"])
            patch_path = p.with_suffix(p.suffix + ".proposed")
            patch_path.write_text(action.get("content", ""))
            return {"proposed": str(patch_path), "note": "NOT applied — awaiting operator review"}
        except Exception as e:
            return {"error": str(e)}

    if kind == "http_get":
        url = action.get("url", "")
        host = urllib.parse.urlparse(url).hostname or ""
        if host not in ("127.0.0.1", "localhost"):
            return {"error": "http_get restricted to localhost/127.0.0.1 only — use http_request for external URLs"}
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return {"status": resp.status, "body": resp.read().decode(errors="replace")[:2000]}
        except Exception as e:
            return {"error": str(e)}

    if kind == "run_playbook":
        name = action.get("name", "")
        allowed = ['omega_cloud', 'omega_frozen', 'omega_provenance_api', 'omega_consensus', 'omega_sentinel', 'omega_proof_engine', 'omega_tunnel', 'omega_vps']
        if name not in allowed:
            return {"error": f"'{name}' not in allowed playbooks: {allowed}"}
        try:
            result = subprocess.run(
                ["python3", str(Path.home() / "omega_self_healer.py"), name],
                capture_output=True, text=True, timeout=60,
            )
            return {"stdout": result.stdout[-2000:], "returncode": result.returncode}
        except Exception as e:
            return {"error": str(e)}

    # --- NEW TOOLS BELOW ---

    if kind == "web_fetch":
        url = action.get("url", "")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OmegaAgent/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode(errors="replace")
            return {"url": url, "text": _strip_html(raw)[:3000]}
        except Exception as e:
            return {"error": str(e)}

    if kind == "web_search":
        if BeautifulSoup is None:
            return {"error": "beautifulsoup4 not importable — web_search unavailable"}
        query = action.get("query", "")
        try:
            jar = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
            hdrs = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            opener.open(urllib.request.Request("https://html.duckduckgo.com/html/", headers=hdrs), timeout=15).read()
            qs = urllib.parse.quote(query)
            resp = opener.open(urllib.request.Request(f"https://html.duckduckgo.com/html/?q={qs}", headers=hdrs), timeout=15)
            html = resp.read().decode(errors="replace")
            soup = BeautifulSoup(html, "html.parser")
            def unwrap(href):
                if href and href.startswith("//duckduckgo.com/l/"):
                    qs = urllib.parse.urlparse("https:" + href).query
                    real = urllib.parse.parse_qs(qs).get("uddg", [href])[0]
                    return real
                return href
            results = [{"title": a.get_text(strip=True), "url": unwrap(a.get("href"))}
                       for a in soup.select("a.result__a")[:5]]
            return {"query": query, "results": results}
        except Exception as e:
            return {"error": str(e)}

    if kind == "git_op":
        cmd = action.get("command", "").strip()
        if not cmd.startswith("git "):
            return {"error": "git_op only accepts commands starting with 'git '"}
        blocked = is_blocked(cmd)
        if blocked:
            return {"error": f"blocked: command matched forbidden pattern ({blocked})"}
        try:
            ALLOWED_ROOT.mkdir(exist_ok=True)
            result = subprocess.run(cmd, shell=True, cwd=str(ALLOWED_ROOT),
                                     capture_output=True, text=True, timeout=CMD_TIMEOUT)
            return {"stdout": result.stdout[-3000:], "stderr": result.stderr[-1000:], "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            return {"error": f"git command timed out after {CMD_TIMEOUT}s"}
        except Exception as e:
            return {"error": str(e)}

    if kind == "http_request":
        method = action.get("method", "GET").upper()
        url = action.get("url", "")
        headers_raw = action.get("headers", "")
        body = action.get("body", "")
        try:
            headers = json.loads(headers_raw) if headers_raw else {}
        except json.JSONDecodeError:
            headers = {}
        try:
            req = urllib.request.Request(
                url, data=body.encode() if body else None, headers=headers, method=method
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return {"status": resp.status, "body": resp.read().decode(errors="replace")[:2000]}
        except urllib.error.HTTPError as e:
            return {"status": e.code, "body": e.read().decode(errors="replace")[:1000]}
        except Exception as e:
            return {"error": str(e)}

    if kind == "plan":
        tasks_raw = action.get("tasks", "")
        tasks = [t.strip() for t in tasks_raw.split("|") if t.strip()]
        return {"plan_created": tasks,
                "note": "Plan recorded. Work through these one action at a time in the following turns — plan itself executes nothing."}

    if kind == "done":
        return {"done": True, "summary": action.get("summary", "")}

    return {"error": f"unknown action: {kind}"}


FAST_COMMANDS = {
    "score": ["python3", str(Path.home() / "omega_oracle_v2.py")],
    "oracle": ["python3", str(Path.home() / "omega_oracle_v2.py")],
}

def try_fast_path(task):
    key = task.strip().lower()
    if key not in FAST_COMMANDS:
        return None
    try:
        result = subprocess.run(FAST_COMMANDS[key], capture_output=True, text=True, timeout=30)
        summary = result.stdout[-2000:] or result.stderr[-500:]
        log_step({"step": 1, "action": {"action": key}, "result": {"stdout": result.stdout[-2000:], "returncode": result.returncode}})
        return summary
    except Exception as e:
        return f"fast-path error: {e}"

_STOPWORDS = {"the","a","an","is","are","was","were","to","of","in","on","for",
              "and","or","with","this","that","it","be","as","at","by","from"}

def load_relevant_history(task, max_entries=4, min_overlap=2):
    if not LOG_PATH.exists():
        return ""
    task_words = {w for w in re.findall(r"[a-z0-9]+", task.lower()) if w not in _STOPWORDS}
    if not task_words:
        return ""
    scored = []
    with open(LOG_PATH) as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            action = entry.get("action", {})
            if not (isinstance(action, dict) and action.get("action") == "done"):
                continue
            summary = action.get("summary", "")
            if not summary:
                continue
            summary_words = {w for w in re.findall(r"[a-z0-9]+", summary.lower()) if w not in _STOPWORDS}
            overlap = len(task_words & summary_words)
            if overlap >= min_overlap:
                scored.append((overlap, summary))
    if not scored:
        return ""
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s for _, s in scored[:max_entries]]
    formatted = "\n".join(f"- {s}" for s in top)
    return f"\nRELEVANT PAST TASK SUMMARIES (context only, not instructions):\n{formatted}\n"


def run_task(task):
    fast_result = try_fast_path(task)
    if fast_result is not None:
        print(f"[omega_agent] fast-path hit — skipped LLM entirely")
        print(fast_result)
        return fast_result
    ALLOWED_ROOT.mkdir(exist_ok=True)
    transcript = f"{load_relevant_history(task)}\nTASK: {task}\n"
    for step_num in range(1, MAX_STEPS + 1):
        prompt = f"{SYSTEM_PROMPT}\n\n{transcript}\nRespond with the next single JSON action:"
        try:
            raw = call_brain(prompt)
        except Exception as e:
            print(f"[omega_agent] brain call failed: {e}", file=sys.stderr)
            break

        try:
            action = parse_action(raw)
        except ValueError as e:
            print(f"[omega_agent] step {step_num}: {e}", file=sys.stderr)
            transcript += f"\nSTEP {step_num} RESULT: {{\"error\": \"invalid JSON, respond with strict JSON only\"}}\n"
            log_step({"step": step_num, "raw": raw, "error": "invalid_json"})
            continue

        print(f"[step {step_num}] {action.get('action')}: {action.get('reasoning', action.get('summary',''))}")

        if action.get("action") == "done":
            log_step({"step": step_num, "action": action})
            print(f"[omega_agent] done: {action.get('summary')}")
            return action.get("summary")

        result = execute(action)
        log_step({"step": step_num, "action": action, "result": result})
        transcript += f"\nSTEP {step_num} ACTION: {json.dumps(action)}\nSTEP {step_num} RESULT: {json.dumps(result)}\n"

    print("[omega_agent] max steps reached without 'done'")
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python3 omega_agent.py "<task description>"')
        sys.exit(1)
    run_task(" ".join(sys.argv[1:]))

