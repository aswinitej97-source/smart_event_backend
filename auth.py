import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import jwt, JWTError
from passlib.context import CryptContext

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "")

if len(SECRET_KEY) < 32:
    raise RuntimeError(
        "Run python setup_env.py to configure SECRET_KEY"
    )

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt"],
    deprecated="auto",
)


def hash_password(password):
    return pwd_context.hash(password)


def verify_password(password, hashed_password):
    try:
        return pwd_context.verify(
            password,
            hashed_password,
        )
    except (ValueError, TypeError):
        return False


def create_access_token(data):
    payload = dict(data)

    payload["exp"] = (
        datetime.now(timezone.utc)
        + timedelta(minutes=60)
    )

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm="HS256",
    )


def decode_access_token(token):
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"],
            options={
                "require_exp": True,
                "require_sub": True,
            },
        )
    except JWTError:
        return None