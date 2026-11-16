from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.auth.repository import UserRepository
from app.auth.schemas import AccessTokenResponse, LoginRequest, RegisterRequest, UserResponse
from app.auth.security import create_access_token, hash_password, verify_password
from app.core.config import get_settings
from app.db.models import UserRecord
from app.db.session import get_session

router = APIRouter(prefix="/api/auth", tags=["authentication"])
Session = Annotated[AsyncSession, Depends(get_session)]


def _token_response(user: UserRecord) -> AccessTokenResponse:
    token, expires_in = create_access_token(user.id, get_settings())
    return AccessTokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/register",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(body: RegisterRequest, session: Session) -> AccessTokenResponse:
    repository = UserRepository(session)
    if await repository.get_by_email(str(body.email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered"
        )

    encoded = await asyncio.to_thread(hash_password, body.password)
    try:
        user = await repository.create(str(body.email), encoded, body.display_name)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc
    return _token_response(user)


@router.post("/login", response_model=AccessTokenResponse)
async def login(body: LoginRequest, session: Session) -> AccessTokenResponse:
    user = await UserRepository(session).get_by_email(str(body.email))
    valid = bool(
        user
        and user.is_active
        and user.password_hash
        and await asyncio.to_thread(verify_password, body.password, user.password_hash)
    )
    if not valid or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _token_response(user)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserRecord:
    return user
