import time
import sys
import os

sys.path.append(os.path.expanduser("~/omega_runtime"))
from omega_vps_storage_init import OmegaStorageProvisioner
from omega_settlement import OmegaSettlement

class OmegaSafeScaler(OmegaStorageProvisioner):
    def __init__(self):
        super().__init__()
        self.settlement = OmegaSettlement()
        self.node_cost = 297.00
        self.batch_size = 10  # Provision 10, then cool
        self.cool_down = 30   # Seconds to cool

    def scale_safely(self, start_idx, end_idx):
        print(f"--- OMEGA SAFE-SCALE: {start_idx} TO {end_idx} ---")
        count = 0
        for i in range(start_idx, end_idx + 1):
            node_name = f"storage-node-{i:03d}"
            
            # 1. Settle
            self.settlement.settle(receiver_id="node-002", amount=self.node_cost, resource=f"PROVISION_{node_name.upper()}")
            
            # 2. Provision
            if self.provision_storage_node(i):
                print(f"[{node_name}] LIVE.")
                count += 1
                
                # 3. Throttle
                if count % self.batch_size == 0:
                    print(f"--- THERMAL THROTTLE: COOLING FOR {self.cool_down}s ---")
                    time.sleep(self.cool_down)
                else:
                    time.sleep(3) # Base delay
            else:
                break

if __name__ == "__main__":
    scaler = OmegaSafeScaler()
    # Resume from node 2 (assuming 001 survived the crash)
    scaler.scale_safely(2, 1000)
