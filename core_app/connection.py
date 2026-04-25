from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from core_app.config import settings


class Base(DeclarativeBase):
    pass

engine = create_async_engine(settings.db_url)

session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with session_factory() as session:
        yield session
