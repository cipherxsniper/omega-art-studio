from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from database.db import SessionLocal
from api.auth import generate_api_key
from api.auth import create_jwt

router = APIRouter()


class AuthRequest(BaseModel):
    owner_name: str
    account_id: str


@router.post("/auth/bootstrap")
def bootstrap(payload: AuthRequest):

    db = SessionLocal()

    try:

        api_key = generate_api_key()

        jwt_token = create_jwt(
            payload.account_id
        )

        db.execute(
            text("""
            INSERT INTO api_keys (
                api_key,
                owner_name
            )
            VALUES (
                :api_key,
                :owner_name
            )
            """),
            {
                "api_key": api_key,
                "owner_name": payload.owner_name
            }
        )

        db.commit()

        return {
            "api_key": api_key,
            "jwt": jwt_token
        }

    finally:
        db.close()
