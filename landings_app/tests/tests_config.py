import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt

from landings_app.services import get_redis, token_auth
from landings_app.main import app

AFFILIATE_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OFFER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
JWT_SECRET = "test-secret"
JWT_ALGORITHM = "HS256"


def make_token(affiliate_id: uuid.UUID = AFFILIATE_ID, secret: str = JWT_SECRET) -> str:
    return jwt.encode({"id": str(affiliate_id)}, secret, algorithm=JWT_ALGORITHM)


def valid_lead_payload(affiliate_id: uuid.UUID = AFFILIATE_ID) -> dict:
    return {
        "name": "John Doe",
        "phone": "+1234567890",
        "country": "US",
        "offer_id": str(OFFER_ID),
        "affiliate_id": str(affiliate_id),
    }

@pytest.fixture()
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.lpush = AsyncMock(return_value=1)
    return redis


@pytest_asyncio.fixture()
async def client(mock_redis: AsyncMock) -> AsyncClient:
    app.dependency_overrides[token_auth] = lambda: AFFILIATE_ID
    app.dependency_overrides[get_redis] = lambda: mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
