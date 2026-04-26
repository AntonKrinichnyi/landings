from uuid import UUID
from uuid import uuid4
from datetime import datetime

import pytest
import pytest_asyncio
from jose import jwt
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient

from core_app.main import app
from core_app.models import Lead, Offer
from core_app.services import get_redis, token_auth
from core_app.db.connection import get_db

AFFILIATE_ID = UUID("11111111-1111-1111-1111-111111111111")
OFFER_ID = UUID("22222222-2222-2222-2222-222222222222")
JWT_SECRET = "test-secret-token"
JWT_ALGORITHM = "HS256"


def create_test_token(
    affiliate_id: UUID = AFFILIATE_ID, token: str = JWT_SECRET
) -> str:
    return jwt.encode({"id": str(affiliate_id)}, token, algorithm=JWT_ALGORITHM)


def make_lead(
    name: str = "Valera",
    phone: str = "+380666666666",
    country: str = "CN",
    offer_id: UUID = OFFER_ID,
    affiliate_id: UUID = AFFILIATE_ID,
    created_at: datetime = datetime(2026, 4, 24, 10, 0, 0),
    offer_name: str = "Test_case Offer",
) -> Lead:
    offer = Offer(id=offer_id, name=offer_name)
    lead = Lead(
        id=uuid4(),
        name=name,
        phone=phone,
        country=country,
        offer_id=offer_id,
        affiliate_id=affiliate_id,
        created_at=created_at,
    )
    lead.offer = offer

    return lead

def _set_db_leads(session: AsyncMock, leads: list) -> None:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = leads
    session.execute = AsyncMock(return_value=mock_result)

@pytest.fixture()
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.brpop = AsyncMock(return_value=None)
    return redis


@pytest.fixture()
def mock_db_session() -> AsyncMock:
    session = AsyncMock()
    _set_db_leads(session, [])
    return session


@pytest_asyncio.fixture()
async def client(mock_db_session: AsyncMock, mock_redis: AsyncMock) -> AsyncClient:
    app.dependency_overrides[token_auth] = lambda: AFFILIATE_ID
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_redis] = lambda: mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
