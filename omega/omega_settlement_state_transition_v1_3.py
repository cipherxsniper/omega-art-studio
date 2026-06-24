from omega_db_kernel_v1 import OmegaTransaction
from omega_settlement_state_machine_v1 import (
    SETTLEMENT_ID,
    STATE,
    get_state,
    set_state
)

def advance_state(cur):
    state = get_state(cur)

    if state == STATE["PENDING"]:
        set_state(cur, STATE["SETTLED"])
        return {"status": "MOVED_TO_SETTLED"}

    if state == STATE["SETTLED"]:
        set_state(cur, STATE["FINALIZED"])
        return {"status": "MOVED_TO_FINALIZED"}

    if state == STATE["FINALIZED"]:
        set_state(cur, STATE["SEALED"])
        return {"status": "MOVED_TO_SEALED"}

    return {"status": state}

if __name__ == "__main__":
    with OmegaTransaction() as cur:
        result = advance_state(cur)
        print(result)
