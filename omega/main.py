from fastapi import FastAPI
from core.freeze_guard import enforce_freeze

app = FastAPI()

# 🔒 HARD FREEZE CHECK (RUNS BEFORE ANY ROUTES LOAD)
enforce_freeze()

from api.routes.transactions import router as transactions_router
app.include_router(transactions_router)
