from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from jwt import InvalidTokenError

from app.core.config import Settings

ALGORITHM = "HS256"
TOKEN_TYPE = "access"
password_hasher = PasswordHasher()


class InvalidAccessTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except (InvalidHashError, VerificationError):
        return False


def create_access_token(user_id: UUID, settings: Settings) -> tuple[str, int]:
    now = datetime.now(UTC)
    expires_in = settings.jwt_access_token_expire_minutes * 60
    payload = {
        "sub": str(user_id),
        "type": TOKEN_TYPE,
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, settings.app_secret_key.get_secret_value(), algorithm=ALGORITHM)
    return token, expires_in


def decode_access_token(token: str, settings: Settings) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.app_secret_key.get_secret_value(),
            algorithms=[ALGORITHM],
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "type", "iss", "iat", "exp"]},
        )
        if payload.get("type") != TOKEN_TYPE:
            raise InvalidAccessTokenError
        return UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise InvalidAccessTokenError from exc
