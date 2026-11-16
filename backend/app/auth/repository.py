from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserRecord


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: UUID) -> UserRecord | None:
        return await self.session.get(UserRecord, user_id)

    async def get_by_email(self, email: str) -> UserRecord | None:
        return await self.session.scalar(
            select(UserRecord).where(UserRecord.email == email.strip().casefold())
        )

    async def create(self, email: str, password_hash: str, display_name: str) -> UserRecord:
        user = UserRecord(
            email=email.strip().casefold(),
            password_hash=password_hash,
            display_name=display_name,
        )
        self.session.add(user)
        await self.session.flush()
        return user
