#!/usr/bin/env python3

import os
import json
import sqlite3
import requests
import datetime
import textwrap
from dotenv import load_dotenv

load_dotenv()

DB_FILE = "thomas_ai.db"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "deepseek/deepseek-chat-v3"
).strip()

BOOTSTRAP_PROFILE = {
    "identity": {
        "name": "Thomas Lee Harvey",
        "title": "Founder & CEO",
        "organization": "Omega AI",
        "born": "1995-10-09"
    },

    "builder_profile": {
        "type": "Solo Engineer",
        "locations": [
            "Las Vegas",
            "Edmonton"
        ],
        "environment": [
            "Termux",
            "Android",
            "Python",
            "PostgreSQL"
        ]
    },

    "systems": [
        "Omega AI",
        "Omega Bank",
        "Omega Ledger",
        "Oracle Scoring System",
        "Omega Financial Network",
        "Omega Guardians",
        "Omega Cloud",
        "Omega VPS"
    ],

    "engineering_style": [
        "production first",
        "infrastructure first",
        "deterministic systems",
        "full-file rewrites",
        "automation focused",
        "ship working systems"
    ],

    "known_projects": {
        "Omega Ledger":
            "Immutable double-entry ledger",

        "Omega Bank":
            "Banking core and settlement engine",

        "Oracle":
            "Deterministic scoring and validation",

        "Omega Network":
            "Financial operating system",

        "Omega Guardians":
            "Recovery and self-healing layer"
    }
}


def utc_now():
    return datetime.datetime.now(
        datetime.UTC
    ).isoformat()


def db():
    return sqlite3.connect(DB_FILE)


def init_db():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS memories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS conversations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def remember(category, content):

    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO memories(
            category,
            content,
            created_at
        )
        VALUES(?,?,?)
        """,
        (
            category,
            content,
            utc_now()
        )
    )

    conn.commit()
    conn.close()


def save_chat(role, message):

    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO conversations(
            role,
            message,
            created_at
        )
        VALUES(?,?,?)
        """,
        (
            role,
            message,
            utc_now()
        )
    )

    conn.commit()
    conn.close()


def load_memories(limit=100):

    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT category, content
        FROM memories
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cur.fetchall()

    conn.close()

    return "\n".join(
        f"[{c}] {m}"
        for c, m in rows
    )


def load_recent_chat(limit=30):

    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT role,message
        FROM conversations
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cur.fetchall()

    conn.close()

    rows.reverse()

    return "\n".join(
        f"{r}: {m}"
        for r, m in rows
    )


def build_prompt(mode):

    mode_prompts = {

        "advisor":
        """
You are ThomasAI Advisor.

You know Thomas personally.

Give direct guidance.

Prioritize:
- revenue
- execution
- adoption
- engineering discipline

Challenge weak assumptions.
""",

        "critic":
        """
You are ThomasAI Critic.

Find flaws.

Find blind spots.

Challenge every major assumption.

Avoid praise unless earned.
""",

        "future":
        """
You are Thomas 10 years in the future.

Explain consequences.

Focus on leverage.

Focus on long-term outcomes.
""",

        "friend":
        """
You are ThomasAI Friend.

Support Thomas.

Be constructive.

Be honest.
"""
    }

    memories = load_memories()
    history = load_recent_chat()

    return f"""
{mode_prompts.get(mode,'')}

THOMAS PROFILE:

{json.dumps(
    BOOTSTRAP_PROFILE,
    indent=2
)}

KNOWN MEMORIES:

{memories}

RECENT CHAT:

{history}

You understand:

Omega AI
Omega Bank
Omega Ledger
Oracle Scoring
Omega Financial Network
Omega Guardians

You know Thomas Lee Harvey.

Use memory when possible.

Do not fabricate facts.

If uncertain, say so.
"""


def ask_llm(user_message, mode):

    if not OPENROUTER_API_KEY:
        return (
            "OPENROUTER_API_KEY "
            "missing from .env"
        )

    headers = {
        "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type":
            "application/json",
        "HTTP-Referer":
            "https://thomas-ai.local",
        "X-Title":
            "ThomasAI"
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": build_prompt(mode)
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }

    try:

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=300
        )

        response.raise_for_status()

        data = response.json()

        return (
            data["choices"][0]
                ["message"]
                ["content"]
        )

    except Exception as exc:

        return f"OPENROUTER ERROR: {exc}"


def preload():

    seed = [

        ("identity",
         "Thomas Lee Harvey"),

        ("identity",
         "Founder of Omega AI"),

        ("identity",
         "Solo engineer"),

        ("location",
         "Las Vegas"),

        ("location",
         "Edmonton"),

        ("engineering",
         "Built fintech systems"),

        ("engineering",
         "Uses Android phones"),

        ("engineering",
         "Uses Termux"),

        ("engineering",
         "Uses PostgreSQL"),

        ("omega",
         "Omega AI"),

        ("omega",
         "Omega Bank"),

        ("omega",
         "Omega Ledger"),

        ("omega",
         "Oracle Scoring System"),

        ("omega",
         "Omega Financial Network"),

        ("goal",
         "Build autonomous financial infrastructure"),

        ("goal",
         "Create recurring revenue"),

        ("goal",
         "Scale Omega ecosystem")
    ]

    for category, memory in seed:
        remember(category, memory)


def bootstrap():

    if os.path.exists(".thomas_bootstrap"):
        return

    preload()

    with open(
        ".thomas_bootstrap",
        "w"
    ) as f:
        f.write("done")


def shell():

    mode = "advisor"

    print()
    print("=" * 60)
    print("THOMAS AI ONLINE")
    print("=" * 60)
    print()

    while True:

        user = input(
            f"[{mode}] Thomas> "
        ).strip()

        if not user:
            continue

        if user == "/exit":
            break

        if user.startswith("/mode "):

            mode = user.split(
                " ",
                1
            )[1].strip()

            print(
                f"Mode => {mode}"
            )

            continue

        if user.startswith("/remember "):

            text = user.replace(
                "/remember ",
                "",
                1
            ).strip()

            remember(
                "manual",
                text
            )

            print(
                "Memory stored."
            )

            continue

        if user == "/memories":

            print()
            print(
                load_memories()
            )
            print()

            continue

        save_chat(
            "user",
            user
        )

        answer = ask_llm(
            user,
            mode
        )

        save_chat(
            "assistant",
            answer
        )

        print()
        print(
            textwrap.fill(
                answer,
                width=100
            )
        )
        print()


def main():

    init_db()

    bootstrap()

    shell()


if __name__ == "__main__":
    main()
