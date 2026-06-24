#!/bin/bash
COUNT=$(PGCONNECT_TIMEOUT=3 psql -h 127.0.0.1 -p 5432 -U postgres -d omega_bank -t -c "SELECT COUNT(*) FROM ledger_entries WHERE om109_fingerprint IS NULL AND event_type NOT IN ('STRESS_TEST','STRESS_BILLION')" 2>/dev/null | tr -d '[:space:]')
test "$COUNT" -eq 0
