#!/usr/bin/env python3

import psycopg2
import time

DB_CONFIG = {
    "dbname": "omega_bank",
    "user": "omega"
}

class SQLGuard:

    def __init__(self):
        self.conn = None
        self.connect()

    def connect(self):
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.conn.autocommit = False
            print("[SQL-GUARD] Connected to omega_bank")
        except Exception as e:
            print("[SQL-GUARD] Connection failed:", e)
            time.sleep(2)
            self.connect()

    def ensure_semicolon(self, query):
        q = query.strip()
        if not q.endswith(";"):
            q += ";"
        return q

    def execute(self, query, params=None):
        query = self.ensure_semicolon(query)

        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description:
                    return cur.fetchall()
                return []

        except psycopg2.ProgrammingError as e:
            self.conn.rollback()
            print("[SQL-GUARD][SYNTAX ERROR]", str(e))
            return []

        except psycopg2.OperationalError as e:
            print("[SQL-GUARD][CONNECTION LOST] Reconnecting...")
            self.connect()
            return []

        except Exception as e:
            self.conn.rollback()
            print("[SQL-GUARD][FATAL]", str(e))
            return []

    def safe_query(self, query):
        return self.execute(query)


if __name__ == "__main__":
    guard = SQLGuard()

    while True:
        cmd = input("omega_sql> ")

        if cmd.lower() in ["exit", "quit"]:
            break

        result = guard.safe_query(cmd)
        print(result)
