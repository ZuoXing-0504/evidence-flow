from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.repository import UserRepository
from app.auth.security import InvalidAccessTokenError, decode_access_token
from app.core.config import get_settings
from app.db.models import UserRecord
from app.db.session import get_session

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing access token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserRecord:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise _unauthorized()
    try:
        user_id = decode_access_token(credentials.credentials, get_settings())
    except InvalidAccessTokenError as exc:
        raise _unauthorized() from exc

    user = await UserRepository(session).get(user_id)
    if user is None or not user.is_active or user.password_hash is None:
        raise _unauthorized()
    return user


CurrentUser = Annotated[UserRecord, Depends(get_current_user)]
