from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from uuid import uuid4

from database.db import SessionLocal

router = APIRouter()


class WalletCreate(BaseModel):
    account_id: str
    currency: str = "USD"


@router.post("/wallets")
def create_wallet(payload: WalletCreate):

    db = SessionLocal()

    try:

        wallet_id = str(uuid4())

        db.execute(
            text("""
            INSERT INTO wallets (
                id,
                account_id,
                currency,
                available_balance,
                pending_balance
            )
            VALUES (
                :id,
                :account_id,
                :currency,
                0,
                0
            )
            """),
            {
                "id": wallet_id,
                "account_id": payload.account_id,
                "currency": payload.currency
            }
        )

        db.commit()

        return {
            "status": "WALLET_CREATED",
            "wallet_id": wallet_id,
            "currency": payload.currency
        }

    finally:
        db.close()
