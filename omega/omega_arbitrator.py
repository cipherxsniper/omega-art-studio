import os
import shutil
from omega_settlement import OmegaSettlement

class OmegaArbitrator(OmegaSettlement):
    def __init__(self):
        super().__init__()
        self.storage_threshold = 0.90  # 90% full triggers arbitrage
        self.backup_cost = 1000.00    # OC cost for emergency backup

    def check_system_stress(self):
        """Monitor physical node constraints."""
        total, used, free = shutil.disk_usage("/")
        usage_ratio = used / total
        print(f"--- OMEGA SYSTEM MONITOR ---")
        print(f"Node-001 Storage Usage: {usage_ratio:.2%}")
        return usage_ratio > self.storage_threshold

    def execute_arbitrage(self):
        """Automatically rebalance resources via economic settlement."""
        if self.check_system_stress():
            print("CRITICAL: Storage Threshold Exceeded.")
            print("ACTION: Initiating Autonomous Backup Arbitrage...")
            
            # 1. Execute the settlement
            self.settle(
                receiver_id="node-002", 
                amount=self.backup_cost, 
                resource="EMERGENCY_STORAGE_LEASE_P2"
            )
            
            # 2. In a real scenario, this would trigger:
            # os.system("tar -czf - /home/ubuntu/omega_runtime/storage | ssh node-002 ...")
            print("STATUS: Data Migration Instruction Sent to Sentinel.")
        else:
            print("STATUS: System Balanced. No Arbitrage Required.")

if __name__ == "__main__":
    oaa = OmegaArbitrator()
    # Forcing a test run by lowering threshold for demonstration
    oaa.storage_threshold = 0.10 
    oaa.execute_arbitrage()
