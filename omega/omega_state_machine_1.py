from enum import Enum
import uuid
import json
import time

class WalletState(Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    RESTRICTED = "RESTRICTED"
    CLOSED = "CLOSED"

class AuthState(Enum):
    INITIATED = "INITIATED"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    SETTLED = "SETTLED"
    REVERSED = "REVERSED"
    EXPIRED = "EXPIRED"
    DISPUTED = "DISPUTED"

class StateMachine:
    def __init__(self):
        self.log_file = "omega_state_transitions.log"

    def transition(self, entity_id, from_state, to_state, event_type):
        event = {
            "transition_id": str(uuid.uuid4()),
            "entity_id": entity_id,
            "from": from_state,
            "to": to_state,
            "event_type": event_type,
            "timestamp": time.time()
        }

        with open(self.log_file, "a") as f:
            f.write(json.dumps(event) + "\n")

        return event
