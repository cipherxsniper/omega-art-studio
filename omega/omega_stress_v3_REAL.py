import os
import hashlib
import time
import uuid
import subprocess

class OmegaStressV3Real:
    def __init__(self):
        self.total_tx = 500000
        self.batch_size = 5000 
        self.db_host = "127.0.0.1" 
        self.db_name = "omega_bank"

    def om109_sign(self, data, prev):
        key_a = hashlib.sha256(b"OMEGA_MASTER_A").hexdigest()
        key_b = hashlib.sha256(f"OMEGA_MASTER_B|{prev}".encode()).hexdigest()
        return hashlib.sha256(f"{key_a}|{data}|{key_b}".encode()).hexdigest()

    def run(self):
        print(f"\U0001f525 OMEGA REAL STRESS TEST V3: {self.total_tx:,} TX")
        start = time.time()
        prev = "GENESIS"
        for i in range(0, self.total_tx, self.batch_size):
            sql = "BEGIN;\n"
            for j in range(self.batch_size):
                fp = self.om109_sign(f"TX_{i+j}", prev)
                sql += f"INSERT INTO ledger_entries (transaction_id, payload, om109_fingerprint) VALUES ('{uuid.uuid4()}', 'STRESS_TX', '{fp}');\n"
                prev = fp
            sql += "COMMIT;"
            with open("batch.sql", "w") as f: f.write(sql)
            subprocess.run(["psql", "-h", self.db_host, "-d", self.db_name, "-f", "batch.sql"], capture_output=True)
            print(f"PROGRESS: {i+self.batch_size:,} / {self.total_tx:,} | REAL TPS: {(i+self.batch_size)/(time.time()-start):.2f}")
        print(f"SUCCESS. TOTAL TIME: {time.time()-start:.2f}s")

if __name__ == "__main__":
    OmegaStressV3Real().run()
