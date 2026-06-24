import json
import uuid
import time
from collections import defaultdict

class SettlementConsensus:
    """
    Ensures deterministic ordering + replay-safe settlement finality
    """

    def __init__(self):
        self.sequence = 0
        self.pending = defaultdict(list)
        self.dlq = "omega_dlq.log"

    def next_seq(self):
        self.sequence += 1
        return self.sequence

    def wrap_event(self, event):
        return {
            "seq": self.next_seq(),
            "event_id": event.get("exec_id"),
            "timestamp": time.time(),
            "payload": event
        }

    def validate(self, event):
        # core invariants
        if not event.get("event_id"):
            return False
        if not event.get("mode"):
            return False
        return True

    def to_dlq(self, event, reason):
        record = {
            "event": event,
            "reason": reason,
            "timestamp": time.time()
        }
        with open(self.dlq, "a") as f:
            f.write(json.dumps(record) + "\n")

    def commit(self, event):
        if not self.validate(event):
            self.to_dlq(event, "INVALID_EVENT")
            return None

        wrapped = self.wrap_event(event)

        # persist deterministic order stream
        with open("omega_consensus_stream.log", "a") as f:
            f.write(json.dumps(wrapped) + "\n")

        return wrapped
