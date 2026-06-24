import uuid
import json
from datetime import datetime

class ExecutionLedger:
    def __init__(self):
        self.log_file = "omega_execution_ledger.log"

    def record(self, execution_id, mode, input_data, status, output=None, error=None):
        event = {
            "execution_id": execution_id,
            "timestamp": datetime.utcnow().isoformat(),
            "mode": mode,
            "input": input_data,
            "status": status,
            "output": output,
            "error": str(error) if error else None
        }

        with open(self.log_file, "a") as f:
            f.write(json.dumps(event) + "\n")

    def new_id(self):
        return str(uuid.uuid4())
