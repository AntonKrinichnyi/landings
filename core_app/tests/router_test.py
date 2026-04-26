import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from fastapi import status

from core_app.main import app
from core_app.tests.services_for_tests import (
    OFFER_ID,
    _set_db_leads,
    make_lead,
    client,
    mock_db_session,
    mock_redis
)


class TestLeadsAuth:
    @pytest.mark.asyncio
    async def test_no_token_returns_401(self):
        app.dependency_overrides.clear()

        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(
                "/leads",
                params={"date_from": "2026-01-01", "date_to": "2026-12-31", "group": "date"},
            )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self):
        app.dependency_overrides.clear()

        with patch("core_app.services.settings") as ms:
            ms.jwt_secret = "test-secret"
            ms.jwt_algorithm = "HS256"
            from httpx import ASGITransport, AsyncClient

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get(
                    "/leads",
                    headers={"Authorization": "Bearer bad.token"},
                    params={"date_from": "2026-01-01", "date_to": "2026-12-31", "group": "date"},
                )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestLeadsValidation:
    @pytest.mark.asyncio
    async def test_missing_date_from_returns_422(self, client: AsyncClient):
        resp = await client.get("/leads", params={"date_to": "2026-12-31", "group": "date"})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_missing_date_to_returns_422(self, client: AsyncClient):
        resp = await client.get("/leads", params={"date_from": "2026-01-01", "group": "date"})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_missing_group_returns_422(self, client: AsyncClient):
        resp = await client.get("/leads", params={"date_from": "2026-01-01", "date_to": "2026-12-31"})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_invalid_group_value_returns_422(self, client: AsyncClient):
        resp = await client.get(
            "/leads",
            params={"date_from": "2026-01-01", "date_to": "2026-12-31", "group": "invalid"},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_invalid_date_format_returns_422(self, client: AsyncClient):
        resp = await client.get(
            "/leads",
            params={"date_from": "not-a-date", "date_to": "2026-12-31", "group": "date"},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLeadsGroupByDate:
    @pytest.mark.asyncio
    async def test_empty_result(self, client: AsyncClient):
        resp = await client.get(
            "/leads",
            params={"date_from": "2026-01-01", "date_to": "2026-12-31", "group": "date"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_single_lead_creates_one_bucket(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ):
        lead = make_lead(created_at=datetime(2026, 4, 24, 10, 0, 0))
        _set_db_leads(mock_db_session, [lead])

        resp = await client.get(
            "/leads",
            params={"date_from": "2026-04-24", "date_to": "2026-04-24", "group": "date"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) == 1
        assert data[0]["date"] == "2026-04-24"
        assert data[0]["count"] == 1
        assert len(data[0]["leads"]) == 1

    @pytest.mark.asyncio
    async def test_two_leads_same_day_grouped_together(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ):
        leads = [
            make_lead(name="Alice", created_at=datetime(2026, 4, 24, 9, 0, 0)),
            make_lead(name="Bob", created_at=datetime(2026, 4, 24, 15, 0, 0)),
        ]
        _set_db_leads(mock_db_session, leads)

        resp = await client.get(
            "/leads",
            params={"date_from": "2026-04-24", "date_to": "2026-04-24", "group": "date"},
        )
        data = resp.json()
        assert len(data) == 1
        assert data[0]["count"] == 2

    @pytest.mark.asyncio
    async def test_leads_on_different_days_create_separate_buckets(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ):
        leads = [
            make_lead(name="Alice", created_at=datetime(2026, 4, 23, 10, 0, 0)),
            make_lead(name="Bob", created_at=datetime(2026, 4, 24, 10, 0, 0)),
        ]
        _set_db_leads(mock_db_session, leads)

        resp = await client.get(
            "/leads",
            params={"date_from": "2026-04-23", "date_to": "2026-04-24", "group": "date"},
        )
        data = resp.json()
        assert len(data) == 2
        dates = [d["date"] for d in data]
        assert "2026-04-23" in dates
        assert "2026-04-24" in dates

    @pytest.mark.asyncio
    async def test_buckets_are_sorted_by_date(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ):
        leads = [
            make_lead(name="C", created_at=datetime(2026, 4, 26, 1, 0, 0)),
            make_lead(name="A", created_at=datetime(2026, 4, 24, 1, 0, 0)),
            make_lead(name="B", created_at=datetime(2026, 4, 25, 1, 0, 0)),
        ]
        _set_db_leads(mock_db_session, leads)

        resp = await client.get(
            "/leads",
            params={"date_from": "2026-04-24", "date_to": "2026-04-26", "group": "date"},
        )
        data = resp.json()
        dates = [d["date"] for d in data]
        assert dates == sorted(dates)


class TestLeadsGroupByOffer:
    @pytest.mark.asyncio
    async def test_empty_result(self, client: AsyncClient):
        resp = await client.get(
            "/leads",
            params={"date_from": "2026-01-01", "date_to": "2026-12-31", "group": "offer"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_single_offer_bucket(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ):
        lead = make_lead(offer_name="Summer Deal")
        _set_db_leads(mock_db_session, [lead])

        resp = await client.get(
            "/leads",
            params={"date_from": "2026-01-01", "date_to": "2026-12-31", "group": "offer"},
        )
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Summer Deal"
        assert data[0]["count"] == 1

    @pytest.mark.asyncio
    async def test_two_leads_same_offer_grouped_together(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ):
        leads = [
            make_lead(name="Alice", offer_id=OFFER_ID, offer_name="Campaign A"),
            make_lead(name="Bob", offer_id=OFFER_ID, offer_name="Campaign A"),
        ]
        _set_db_leads(mock_db_session, leads)

        resp = await client.get(
            "/leads",
            params={"date_from": "2026-01-01", "date_to": "2026-12-31", "group": "offer"},
        )
        data = resp.json()
        assert len(data) == 1
        assert data[0]["count"] == 2
        assert data[0]["name"] == "Campaign A"

    @pytest.mark.asyncio
    async def test_different_offers_create_separate_buckets(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ):
        offer_a = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        offer_b = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        leads = [
            make_lead(name="Alice", offer_id=offer_a, offer_name="Offer A"),
            make_lead(name="Bob", offer_id=offer_b, offer_name="Offer B"),
        ]
        _set_db_leads(mock_db_session, leads)

        resp = await client.get(
            "/leads",
            params={"date_from": "2026-01-01", "date_to": "2026-12-31", "group": "offer"},
        )
        data = resp.json()
        assert len(data) == 2
        names = {g["name"] for g in data}
        assert names == {"Offer A", "Offer B"}

    @pytest.mark.asyncio
    async def test_response_contains_lead_details(
        self, client: AsyncClient, mock_db_session: AsyncMock
    ):
        lead = make_lead(name="Charlie", phone="+1999", country="PL")
        _set_db_leads(mock_db_session, [lead])

        resp = await client.get(
            "/leads",
            params={"date_from": "2026-01-01", "date_to": "2026-12-31", "group": "offer"},
        )
        lead_data = resp.json()[0]["leads"][0]
        assert lead_data["name"] == "Charlie"
        assert lead_data["phone"] == "+1999"
        assert lead_data["country"] == "PL"
