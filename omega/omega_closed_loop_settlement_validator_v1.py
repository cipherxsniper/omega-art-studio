import sqlite3
import ast

DB = "omega_ledger.db"

def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT payload FROM ledger_events")
    rows = cur.fetchall()

    totals = {
        "OMEGA_TREASURY": 0,
        "OMEGA_CREDIT": 0,
        "OMEGA_INVESTMENT": 0,
        "THOMAS_LH": 0
    }

    for r in rows:
        try:
            payload = ast.literal_eval(r[0])
            for k, v in payload.items():
                totals[k] += v
        except:
            continue

    print("🧠 CLOSED LOOP VALIDATION")
    print(totals)

    net = sum(totals.values())
    print("NET SYSTEM BALANCE:", net)

    conn.close()

if __name__ == "__main__":
    run()
