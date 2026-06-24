from dataclasses import dataclass
import sqlite3

DB = "omega_ledger.db"

ALIASES = {
    "RESERVE": "OMEGA_RESERVE",
    "TREASURY": "OMEGA_TREASURY",
    "INVESTMENT": "OMEGA_INVESTMENT",
    "CREDIT": "OMEGA_CREDIT",
    "THOMAS": "THOMAS_LH",
    "REVENUE": "REVENUE",
    "SYSTEM": "SYSTEM"
}

def resolve_account(name: str) -> str:
    return ALIASES.get(name.upper(), name)

def get_account(conn, name: str):
    name = resolve_account(name)
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, balance FROM accounts WHERE user_id = ?", (name,))
    return cur.fetchone()

def ensure_account(conn, name: str):
    name = resolve_account(name)
    cur = conn.cursor()
    cur.execute("SELECT id FROM accounts WHERE user_id = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        "INSERT INTO accounts (id, user_id, balance) VALUES (?, ?, ?)",
        (name, name, 0.0)
    )
    conn.commit()
    return name
