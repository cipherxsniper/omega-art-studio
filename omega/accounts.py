from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from uuid import uuid4

from database.db import SessionLocal

router = APIRouter()


class AccountCreate(BaseModel):
    owner_name: str


@router.post("/accounts")
def create_account(payload: AccountCreate):

    db = SessionLocal()

    try:

        account_id = str(uuid4())

        db.execute(
            text("""
            INSERT INTO accounts (
                id,
                owner_name
            )
            VALUES (
                :id,
                :owner_name
            )
            """),
            {
                "id": account_id,
                "owner_name": payload.owner_name
            }
        )

        db.commit()

        return {
            "status": "ACCOUNT_CREATED",
            "account_id": account_id,
            "owner_name": payload.owner_name
        }

    finally:
        db.close()
