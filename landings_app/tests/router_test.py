import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import status

from landings_app.services import get_redis, token_auth
from landings_app.main import app
from landings_app.tests.tests_config import (
    AFFILIATE_ID,
    JWT_SECRET,
    OFFER_ID,
    make_token,
    valid_lead_payload,
    mock_redis,
    client
)


class TestIngestLeadSuccess:
    @pytest.mark.asyncio
    async def test_returns_200_and_queued(self, client: AsyncClient, mock_redis: AsyncMock):
        response = await client.post("/lead", json=valid_lead_payload())
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "queued"}

    @pytest.mark.asyncio
    async def test_pushes_to_redis_queue(self, client: AsyncClient, mock_redis: AsyncMock):
        payload = valid_lead_payload()
        await client.post("/lead", json=payload)
        mock_redis.lpush.assert_awaited_once()
        queue_name, raw_json = mock_redis.lpush.call_args.args
        assert queue_name == "leads:queue"
        enqueued = json.loads(raw_json)
        assert enqueued["name"] == payload["name"]
        assert enqueued["phone"] == payload["phone"]

    @pytest.mark.asyncio
    async def test_enqueued_payload_matches_request(self, client: AsyncClient, mock_redis: AsyncMock):
        payload = valid_lead_payload()
        await client.post("/lead", json=payload)
        _, raw_json = mock_redis.lpush.call_args.args
        enqueued = json.loads(raw_json)
        assert enqueued["country"] == "US"
        assert enqueued["offer_id"] == str(OFFER_ID)
        assert enqueued["affiliate_id"] == str(AFFILIATE_ID)


class TestIngestLeadAffiliateMismatch:
    @pytest.mark.asyncio
    async def test_returns_403_when_affiliate_id_does_not_match_jwt(self, mock_redis: AsyncMock):
        other_affiliate = uuid.UUID("99999999-9999-9999-9999-999999999999")
        app.dependency_overrides[token_auth] = lambda: AFFILIATE_ID
        app.dependency_overrides[get_redis] = lambda: mock_redis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/lead", json=valid_lead_payload(affiliate_id=other_affiliate))

        app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "affiliate_id" in response.json()["detail"]


class TestIngestLeadAuth:
    @pytest.mark.asyncio
    async def test_missing_token_returns_401(self):
        app.dependency_overrides.clear()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/lead", json=valid_lead_payload())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self):
        app.dependency_overrides.clear()
        with patch("landings_app.services.settings") as mock_settings:
            mock_settings.jwt_secret = JWT_SECRET
            mock_settings.jwt_algorithm = "HS256"
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/lead",
                    json=valid_lead_payload(),
                    headers={"Authorization": "Bearer invalid.token.here"},
                )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestIngestLeadValidation:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad_country", ["us", "USA", "1U", ""])
    async def test_invalid_country_returns_422(self, client: AsyncClient, bad_country: str):
        payload = {**valid_lead_payload(), "country": bad_country}
        response = await client.post("/lead", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @pytest.mark.parametrize("field", ["name", "phone", "country", "offer_id", "affiliate_id"])
    async def test_missing_field_returns_422(self, client: AsyncClient, field: str):
        payload = valid_lead_payload()
        del payload[field]
        response = await client.post("/lead", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_empty_body_returns_422(self, client: AsyncClient):
        response = await client.post("/lead", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
