#!/usr/bin/env python3

import sys
import subprocess
import psycopg2

DB = {
    "dbname": "omega_bank",
    "user": "omega",
    "host": "localhost",
    "port": 5432
}

def run_sql(sql):
    from omega_execution_gate import gate
    gate(sql)

    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    cur.execute(sql)

    try:
        rows = cur.fetchall()
        for r in rows:
            print(r)
    except:
        pass

    conn.commit()
    conn.close()

if __name__ == "__main__":
    sql = " ".join(sys.argv[1:])
    run_sql(sql)
