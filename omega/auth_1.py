import time
import secrets

from jose import jwt
from fastapi import Header, HTTPException
from sqlalchemy import text

from database.db import SessionLocal

SECRET_KEY = "OMEGA_SUPER_SECRET"
ALGORITHM = "HS256"


def generate_api_key():

    return secrets.token_hex(32)


def create_jwt(account_id):

    payload = {
        "sub": account_id,
        "iat": int(time.time())
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_jwt(token):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="INVALID_TOKEN"
        )


def verify_api_key(x_api_key: str = Header(None)):

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API_KEY_REQUIRED"
        )

    db = SessionLocal()

    try:

        result = db.execute(
            text("""
            SELECT active
            FROM api_keys
            WHERE api_key = :api_key
            """),
            {
                "api_key": x_api_key
            }
        ).fetchone()

        if not result:
            raise HTTPException(
                status_code=401,
                detail="INVALID_API_KEY"
            )

        if not result[0]:
            raise HTTPException(
                status_code=401,
                detail="DISABLED_API_KEY"
            )

        return True

    finally:
        db.close()
