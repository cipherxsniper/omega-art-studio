import time
import sys
import os

# Aligning paths for OMEGA Runtime
sys.path.append(os.path.expanduser("~/omega_runtime"))

from omega_vps_storage_init import OmegaStorageProvisioner
from omega_settlement import OmegaSettlement

class OmegaMassScaler(OmegaStorageProvisioner):
    def __init__(self):
        super().__init__()
        self.settlement = OmegaSettlement()
        self.node_cost = 297.00

    def scale_to_target(self, start_idx, end_idx):
        print(f"--- OMEGA HYPER-STORAGE SCALE: {start_idx} TO {end_idx} ---")
        for i in range(start_idx, end_idx + 1):
            node_name = f"storage-node-{i:03d}"
            
            # 1. Settle the internal cost first (Proof of Capital)
            print(f"[{node_name}] Settling $297.00 OC...")
            try:
                self.settlement.settle(
                    receiver_id="node-002",
                    amount=self.node_cost,
                    resource=f"PROVISION_FEE_{node_name.upper()}"
                )
                
                # 2. Provision the node
                if self.provision_storage_node(i):
                    print(f"[{node_name}] SUCCESS. Scaling next...")
                    time.sleep(1) # Optimal throttle for Termux
                else:
                    print(f"[{node_name}] FAILED. Pausing scale.")
                    break
            except Exception as e:
                print(f"[{node_name}] CRITICAL ERROR: {e}")
                break

if __name__ == "__main__":
    scaler = OmegaMassScaler()
    # TARGET: 100TB (1,000 nodes total)
    # We already have node 001. Starting from 002.
    scaler.scale_to_target(2, 1000)
