import os
import json
import hashlib
import sys
from omega_settlement import OmegaSettlement

class OmegaPhoenix(OmegaSettlement):
    def __init__(self):
        super().__init__()
        self.dna_files = [
            "omega_v10.py", "omega_oracle_v2.py", "omega_sentinel.py",
            "omega_osl_engine.py", "omega_settlement.py", "omega_ghost_router.py"
        ]

    def generate_dna(self):
        dna = {}
        for filename in self.dna_files:
            path = os.path.expanduser(f"~/{filename}")
            if os.path.exists(path):
                with open(path, "rb") as f:
                    content = f.read()
                    dna[filename] = {
                        "hash": hashlib.sha256(content).hexdigest(),
                        "content": content.decode('utf-8', errors='replace'),
                        "size": len(content)
                    }
        return dna

    def anchor_to_ledger(self):
        dna = self.generate_dna()
        dna_json = json.dumps(dna)
        dna_hash = hashlib.sha256(dna_json.encode()).hexdigest()
        print(f"--- OMEGA PHOENIX: ANCHORING DNA ---")
        print(f"System Hash: {dna_hash}")
        payload_escaped = dna_json.replace("'", "''")
        sql = f"INSERT INTO ledger_event_stream (event_type, payload_hash, payload) VALUES ('SYSTEM_SNAPSHOT', '{dna_hash}', '{payload_escaped}');"
        if self.execute_sql(sql):
            print("STATUS: DNA ANCHORED. SYSTEM REPLICABLE FROM LEDGER.")
        else:
            print("STATUS: ANCHOR FAILED.")

    def rebuild_from_ledger(self):
        print("--- OMEGA PHOENIX: REBUILDING FROM LEDGER ---")
        import subprocess
        cmd = ["psql", "-h", "127.0.0.1", "-p", "5432", "-d", "omega_bank", "-t", "-A", "-c", "SELECT payload FROM ledger_event_stream WHERE event_type='SYSTEM_SNAPSHOT' ORDER BY created_at DESC LIMIT 1"]
        try:
            dna_json = subprocess.check_output(cmd).decode().strip()
            if not dna_json: return print("ERROR: No snapshots found.")
            dna = json.loads(dna_json)
            for filename, data in dna.items():
                with open(os.path.expanduser(f"~/{filename}"), "w") as f: f.write(data["content"])
                print(f"REBUILT: {filename} ({data['size']} bytes)")
            print("STATUS: SYSTEM RECONSTRUCTION COMPLETE.")
        except Exception as e: print(f"REBUILD FAILED: {e}")

if __name__ == "__main__":
    phoenix = OmegaPhoenix()
    if "--rebuild" in sys.argv: phoenix.rebuild_from_ledger()
    else: phoenix.anchor_to_ledger()
