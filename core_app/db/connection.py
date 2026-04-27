from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from core_app.config import settings


class Base(DeclarativeBase):
    pass

engine = create_async_engine(settings.db_url)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    """Provide async database session for dependency injection.
    
    Yields an AsyncSession instance for database operations within
    a FastAPI dependency. Automatically handles session cleanup.
    
    Yields:
        AsyncSession: An async database session.
    """
    async with async_session_factory() as session:
        yield session
