#!/usr/bin/env python3

import subprocess
import uuid
import os
import sys

from omega_event_bus import EventBus
from omega_execution_queues import ExecutionQueues
from omega_settlement_consensus import SettlementConsensus
from omega_state_machine import StateMachine

bus = EventBus()
queues = ExecutionQueues()
consensus = SettlementConsensus()
fsm = StateMachine()

class BankingCoreV7:

    def __init__(self):
        print("OMEGA BANKING CORE v7 (STABLE EXECUTION MODE)\n")

    def classify(self, cmd):

        cmd_strip = cmd.strip().lower()

        # SYSTEM OPS (NO CONSENSUS)
        if cmd_strip.startswith("ls ") or cmd_strip.startswith("cat ") or cmd_strip.startswith("pwd"):
            return "SYSTEM"

        # SQL READ OPS (NO CONSENSUS)
        if cmd_strip.startswith("select"):
            return "SQL_READ"

        # SQL WRITE OPS (CONSENSUS REQUIRED)
        if any(cmd_strip.startswith(k) for k in ["insert", "update", "delete"]):
            return "SQL_WRITE"

        # PYTHON FILE EXECUTION
        if cmd_strip.endswith(".py") and os.path.exists(cmd_strip):
            return "PYTHON"

        return "SHELL"

    def execute(self, cmd, mode):

        if mode in ["SQL_READ", "SQL_WRITE"]:
            return subprocess.run(
                ["psql","-U","omega","-d","omega_bank","-c",cmd],
                capture_output=True,text=True
            )

        if mode == "PYTHON":
            return subprocess.run([sys.executable, cmd],
                                  capture_output=True,text=True)

        return subprocess.run(cmd, shell=True,
                              capture_output=True,text=True)

    def run(self):
        while True:
            cmd = input("OMEGA-V7> ").strip()

            if cmd == "exit":
                break

            mode = self.classify(cmd)
            exec_id = str(uuid.uuid4())

            # SYSTEM PATH (NO CONSENSUS)
            if mode == "SYSTEM":
                result = self.execute(cmd, mode)
                print(result.stdout)
                continue

            # SQL READ (NO CONSENSUS)
            if mode == "SQL_READ":
                result = self.execute(cmd, mode)
                print(result.stdout)
                continue

            # FINANCIAL + SQL WRITE → CONSENSUS PATH
            wrapped = consensus.commit({
                "exec_id": exec_id,
                "mode": mode,
                "cmd": cmd
            })

            if not wrapped:
                print("[REJECTED BY CONSENSUS]")
                continue

            fsm.transition(
                entity_id=exec_id,
                from_state="REQUESTED",
                to_state="QUEUED",
                event_type="COMMAND_QUEUED"
            )

            try:
                result = self.execute(cmd, mode)
                output = result.stdout if hasattr(result, "stdout") else str(result)

                fsm.transition(
                    entity_id=exec_id,
                    from_state="QUEUED",
                    to_state="EXECUTED",
                    event_type="COMMAND_EXECUTED"
                )

                bus.publish("banking.v7.executed", {
                    "exec_id": exec_id,
                    "seq": wrapped["seq"],
                    "output": output
                })

                print(output)

            except Exception as e:

                fsm.transition(
                    entity_id=exec_id,
                    from_state="QUEUED",
                    to_state="FAILED",
                    event_type="COMMAND_FAILED"
                )

                bus.publish("banking.v7.failed", {
                    "exec_id": exec_id,
                    "error": str(e)
                })

                print("[V7 ERROR]", e)

if __name__ == "__main__":
    BankingCoreV7().run()
