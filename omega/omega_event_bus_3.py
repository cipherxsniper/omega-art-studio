import json
import time
import uuid

class EventBus:
    def __init__(self, path="omega_event_stream.log"):
        self.path = path

    def publish(self, topic, payload):
        event = {
            "event_id": str(uuid.uuid4()),
            "topic": topic,
            "timestamp": time.time(),
            "payload": payload
        }

        with open(self.path, "a") as f:
            f.write(json.dumps(event) + "\n")

        return event["event_id"]

    def stream(self):
        with open(self.path, "r") as f:
            for line in f:
                yield json.loads(line)
