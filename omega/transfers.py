import uuid

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from database.db import SessionLocal

router = APIRouter()


class TransferRequest(BaseModel):
    sender_wallet: str
    receiver_wallet: str
    amount: float


@router.post("/transfers/internal")
def internal_transfer(payload: TransferRequest):

    db = SessionLocal()

    try:

        sender = db.execute(
            text("""
            SELECT available_balance
            FROM wallets
            WHERE id = :wallet_id
            """),
            {
                "wallet_id": payload.sender_wallet
            }
        ).fetchone()

        if not sender:

            return {
                "status": "FAILED",
                "reason": "SENDER_NOT_FOUND"
            }

        balance = float(sender[0])

        if balance < payload.amount:

            return {
                "status": "DECLINED",
                "reason": "INSUFFICIENT_FUNDS"
            }

        transaction_id = str(uuid.uuid4())

        db.execute(
            text("""
            UPDATE wallets
            SET
                available_balance =
                    available_balance - :amount,

                pending_balance =
                    pending_balance + :amount

            WHERE id = :wallet_id
            """),
            {
                "amount": payload.amount,
                "wallet_id": payload.sender_wallet
            }
        )

        db.execute(
            text("""
            INSERT INTO authorization_holds (
                transaction_id,
                wallet_id,
                amount,
                status
            )
            VALUES (
                :transaction_id,
                :wallet_id,
                :amount,
                'HELD'
            )
            """),
            {
                "transaction_id": transaction_id,
                "wallet_id": payload.sender_wallet,
                "amount": payload.amount
            }
        )

        db.execute(
            text("""
            INSERT INTO settlement_queue (
                transaction_id,
                sender_wallet,
                receiver_wallet,
                amount
            )
            VALUES (
                :transaction_id,
                :sender_wallet,
                :receiver_wallet,
                :amount
            )
            """),
            {
                "transaction_id": transaction_id,
                "sender_wallet": payload.sender_wallet,
                "receiver_wallet": payload.receiver_wallet,
                "amount": payload.amount
            }
        )

        db.commit()

        return {
            "status": "AUTHORIZED",
            "transaction_id": transaction_id,
            "amount": payload.amount
        }

    finally:
        db.close()
