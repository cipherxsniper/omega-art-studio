import sqlite3
import time

DB = "omega_ledger.db"

def run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    print("[STRESS TEST] adaptive SQLite mode starting")

    # get schema dynamically
    cur.execute("PRAGMA table_info(ledger)")
    cols = [c[1] for c in cur.fetchall()]
    print("[SCHEMA]", cols)

    for i in range(100000):
        try:
            if "amount" in cols:
                cur.execute(
                    "INSERT INTO ledger (amount, status) VALUES (?, ?)",
                    (0.01, "STRESS_TEST")
                )
            else:
                # fallback safe insert
                cur.execute(
                    "INSERT INTO ledger DEFAULT VALUES"
                )

            if i % 1000 == 0:
                conn.commit()
                print("committed:", i)

        except Exception as e:
            print("[ERROR]", e)
            break

    conn.commit()
    conn.close()
    print("[DONE] stress complete")

if __name__ == "__main__":
    run()
