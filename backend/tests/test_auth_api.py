from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Database
from app.db.models import Base
from app.db.session import get_session
from app.main import app


async def _auth_client(path: Path) -> AsyncIterator[AsyncClient]:
    database = Database(f"sqlite+aiosqlite:///{path.as_posix()}")
    async with database.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.sessions() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        await database.dispose()


@pytest.mark.asyncio
async def test_register_login_and_current_user(tmp_path: Path) -> None:
    async for client in _auth_client(tmp_path / "auth.db"):
        registration = await client.post(
            "/api/auth/register",
            json={
                "email": "User@Example.com",
                "password": "strong-password-123",
                "display_name": "  Ada   Lovelace  ",
            },
        )
        assert registration.status_code == 201
        assert registration.json()["token_type"] == "bearer"
        assert registration.json()["expires_in"] == 3600
        assert registration.json()["user"]["email"] == "user@example.com"
        assert registration.json()["user"]["display_name"] == "Ada Lovelace"

        login = await client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "strong-password-123"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_duplicate_registration_and_bad_login_are_rejected(tmp_path: Path) -> None:
    async for client in _auth_client(tmp_path / "auth-errors.db"):
        body = {
            "email": "duplicate@example.com",
            "password": "strong-password-123",
            "display_name": "Researcher",
        }
        assert (await client.post("/api/auth/register", json=body)).status_code == 201
        assert (await client.post("/api/auth/register", json=body)).status_code == 409

        bad_password = await client.post(
            "/api/auth/login",
            json={"email": body["email"], "password": "wrong"},
        )
        unknown = await client.post(
            "/api/auth/login",
            json={"email": "unknown@example.com", "password": "wrong"},
        )
        assert bad_password.status_code == 401
        assert unknown.status_code == 401
        assert bad_password.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_auth_input_validation(tmp_path: Path) -> None:
    async for client in _auth_client(tmp_path / "auth-validation.db"):
        invalid_email = await client.post(
            "/api/auth/register",
            json={"email": "invalid", "password": "long-enough", "display_name": "User"},
        )
        short_password = await client.post(
            "/api/auth/register",
            json={"email": "user@example.com", "password": "short", "display_name": "User"},
        )
        assert invalid_email.status_code == 422
        assert short_password.status_code == 422
