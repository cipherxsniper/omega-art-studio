from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from datetime import datetime

from omega_unified_system_orchestrator_v1 import run as orchestrator_run
from event_ledger_engine import get_ledger_snapshot
from settlement_reconciliation_engine import run_reconciliation

app = FastAPI(title="Omega Control Plane API")

# =========================
# AUTH (SIMPLE SAAS KEY)
# =========================
API_KEY = os.getenv("OMEGA_API_KEY")

def auth(key: str):
    if not API_KEY or key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

# =========================
# MODELS
# =========================

class TransferRequest(BaseModel):
    api_key: str
    from_account: str
    to_account: str
    amount: float

# =========================
# HEALTH
# =========================

@app.get("/health")
def health():
    return {
        "status": "ONLINE",
        "time": datetime.utcnow().isoformat()
    }

# =========================
# BANK SNAPSHOT (CORE)
# =========================

@app.get("/bank")
def bank(api_key: str):
    auth(api_key)
    return get_ledger_snapshot()

# =========================
# SYSTEM TOTAL
# =========================

@app.get("/system_total")
def system_total(api_key: str):
    auth(api_key)
    data = get_ledger_snapshot()
    return {
        "total": data.get("total", 0),
        "currency": "USD"
    }

# =========================
# TRANSFER (CONTROLLED)
# =========================

@app.post("/transfer")
def transfer(req: TransferRequest):
    auth(req.api_key)

    result = orchestrator_run({
        "action": "transfer",
        "from": req.from_account,
        "to": req.to_account,
        "amount": req.amount
    })

    return {
        "status": "PENDING",
        "timestamp": datetime.utcnow().isoformat(),
        "result": result
    }

# =========================
# RECONCILIATION
# =========================

@app.get("/reconcile")
def reconcile(api_key: str):
    auth(api_key)
    return run_reconciliation()

# =========================
# EVENT STREAM
# =========================

@app.get("/events")
def events(api_key: str):
    auth(api_key)
    return {
        "events": "FETCH_FROM_LEDGER_ENGINE"
    }
