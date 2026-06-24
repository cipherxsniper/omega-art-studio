import json
import os

class ExecutionQueues:
    def __init__(self):
        self.base = "omega_queues"
        os.makedirs(self.base, exist_ok=True)

    def enqueue(self, queue, event):
        path = f"{self.base}/{queue}.log"
        with open(path, "a") as f:
            f.write(json.dumps(event) + "\n")

    def read(self, queue):
        path = f"{self.base}/{queue}.log"
        if not os.path.exists(path):
            return []

        with open(path, "r") as f:
            return [json.loads(l) for l in f]
