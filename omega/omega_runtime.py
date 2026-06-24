#!/usr/bin/env python3
import subprocess
import uuid
import os
import sys

from omega_event_bus import EventBus
from omega_execution_queues import ExecutionQueues
from omega_settlement_consensus import SettlementConsensus
from omega_state_machine import StateMachine
from omega_state_rules import StateRules

bus = EventBus()
queues = ExecutionQueues()
consensus = SettlementConsensus()
fsm = StateMachine()
rules = StateRules()

def classify(cmd):
    if any(k in cmd.upper() for k in ["SELECT","INSERT","UPDATE","DELETE"]):
        return "SQL"
    if cmd.endswith(".py") and os.path.exists(cmd):
        return "PYTHON"
    return "SHELL"

def run(cmd, mode):
    if mode == "SQL":
        return subprocess.run(["psql","-U","omega","-d","omega_bank","-c",cmd],
                              capture_output=True,text=True)
    if mode == "PYTHON":
        return subprocess.run([sys.executable, cmd],
                              capture_output=True,text=True)
    return subprocess.run(cmd, shell=True, capture_output=True,text=True)

def main():
    print("OMEGA FINANCIAL STATE MACHINE v6 ACTIVE\n")

    while True:
        cmd = input("OMEGA> ").strip()

        if cmd == "exit":
            break

        event = {
            "exec_id": str(uuid.uuid4()),
            "mode": classify(cmd),
            "cmd": cmd
        }

        wrapped = consensus.commit(event)

        if not wrapped:
            print("[REJECTED: CONSENSUS FAILURE]")
            continue

        # STATE MACHINE HOOK (NEW CORE)
        try:
            # Example wallet transition validation hook
            # (real integration happens at ledger mutation layer)
            fsm.transition(
                entity_id=event["exec_id"],
                from_state="UNKNOWN",
                to_state="PROPOSED",
                event_type="EXECUTION_REQUEST"
            )

            result = run(cmd, event["mode"])
            output = result.stdout if hasattr(result, "stdout") else str(result)

            bus.publish("fsm.finalized", {
                "seq": wrapped["seq"],
                "exec_id": event["exec_id"],
                "output": output
            })

            print(output)

        except Exception as e:
            bus.publish("fsm.failed", {
                "exec_id": event["exec_id"],
                "error": str(e)
            })
            print("[FSM ERROR]", e)

if __name__ == "__main__":
    main()
