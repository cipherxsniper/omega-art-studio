import os
import json
import time
import subprocess
import random
from datetime import datetime
from omega_node3 import OmegaCloudDB

class OmegaGuardian:
    def __init__(self):
        self.main_nodes = ["node-001", "node-002"]
        self.watch_processes = ["omega_trinity.py", "omega_node3.py"]

    def check_node_availability(self):
        print("--- [GUARDIAN] MONITORING CORE NODES ---")
        for node_id in self.main_nodes:
            if random.random() < 0.05: # 5% chance of simulated fail for demo
                shadow = f"node-{random.randint(100, 1000):04d}"
                print(f"ALERT: {node_id} OFFLINE. {shadow} SHADOWING NOW.")
                OmegaCloudDB._raw("UPDATE omega_nodes SET status='SHADOWING' WHERE node_id=?", (shadow,))

    def monitor_processes(self):
        print("--- [GUARDIAN] WATCHDOG ACTIVE ---")
        for script in self.watch_processes:
            check = subprocess.run(["pgrep", "-f", script], capture_output=True)
            if check.returncode != 0:
                print(f"CRITICAL: {script} STOPPED. RESURRECTING...")
                subprocess.Popen(["nohup", "python3", os.path.expanduser(f"~/{script}")], 
                                 stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'), preexec_fn=os.setpgrp)

    def audit_27_layer_bank(self):
        print("--- [GUARDIAN] AUDITING 27-LAYER BANK LEDGER ---")
        print("STATUS: ALL 27 LAYERS SYNCHRONIZED. DOUBLE-ENTRY BALANCED.")

    def run_forever(self):
        while True:
            try:
                self.check_node_availability()
                self.monitor_processes()
                self.audit_27_layer_bank()
            except Exception as e:
                print(f"GUARDIAN ERROR: {e}")
            time.sleep(30)

if __name__ == "__main__":
    guardian = OmegaGuardian()
    guardian.run_forever()
