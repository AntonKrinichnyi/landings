import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core_app.worker import DEDUP_TTL, _dedup_key, _process_lead
from core_app.models import Lead
from core_app.tests.services_for_tests import AFFILIATE_ID, OFFER_ID, mock_redis


AFFILIATE_ID = str(uuid.UUID("11111111-1111-1111-1111-111111111111"))
OFFER_ID = str(uuid.UUID("22222222-2222-2222-2222-222222222222"))


def _raw_lead(**overrides) -> str:
    data = {
        "name": "Bob",
        "phone": "+49000000",
        "country": "DE",
        "offer_id": OFFER_ID,
        "affiliate_id": AFFILIATE_ID,
    }
    data.update(overrides)
    return json.dumps(data)


class TestDedupKey:
    def test_returns_expected_format(self):
        key = _dedup_key("Bob", "+49000000", OFFER_ID, AFFILIATE_ID)
        assert key == f"dedup:Bob:+49000000:{OFFER_ID}:{AFFILIATE_ID}"

    def test_different_names_produce_different_keys(self):
        k1 = _dedup_key("Bob", "+49", OFFER_ID, AFFILIATE_ID)
        k2 = _dedup_key("Alice", "+49", OFFER_ID, AFFILIATE_ID)
        assert k1 != k2

    def test_different_phones_produce_different_keys(self):
        k1 = _dedup_key("Bob", "+111", OFFER_ID, AFFILIATE_ID)
        k2 = _dedup_key("Bob", "+222", OFFER_ID, AFFILIATE_ID)
        assert k1 != k2

    def test_different_offers_produce_different_keys(self):
        other_offer = str(uuid.uuid4())
        k1 = _dedup_key("Bob", "+49", OFFER_ID, AFFILIATE_ID)
        k2 = _dedup_key("Bob", "+49", other_offer, AFFILIATE_ID)
        assert k1 != k2


class TestProcessLeadNew:
    @pytest.fixture()
    def redis_new(self) -> AsyncMock:
        """Redis client where SET NX succeeds → lead is genuinely new."""
        r = AsyncMock()
        r.set = AsyncMock(return_value=True)
        return r

    @pytest.mark.asyncio
    async def test_redis_set_called_with_correct_args(self, redis_new: AsyncMock):
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("core_app.worker.async_session_factory", return_value=mock_ctx):
            await _process_lead(redis_new, _raw_lead())

        redis_new.set.assert_awaited_once()
        args, kwargs = redis_new.set.call_args
        assert args[0].startswith("dedup:")
        assert kwargs.get("ex") == DEDUP_TTL
        assert kwargs.get("nx") is True

    @pytest.mark.asyncio
    async def test_lead_added_to_session(self, redis_new: AsyncMock):
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("core_app.worker.async_session_factory", return_value=mock_ctx):
            await _process_lead(redis_new, _raw_lead())

        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_committed(self, redis_new: AsyncMock):
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("core_app.worker.async_session_factory", return_value=mock_ctx):
            await _process_lead(redis_new, _raw_lead())

        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_lead_saved_with_correct_fields(self, redis_new: AsyncMock):

        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("core_app.worker.async_session_factory", return_value=mock_ctx):
            await _process_lead(redis_new, _raw_lead())

        lead: Lead = mock_session.add.call_args.args[0]
        assert isinstance(lead, Lead)
        assert lead.name == "Bob"
        assert lead.phone == "+49000000"
        assert lead.country == "DE"
        assert lead.offer_id == uuid.UUID(OFFER_ID)
        assert lead.affiliate_id == uuid.UUID(AFFILIATE_ID)


class TestProcessLeadDuplicate:
    @pytest.fixture()
    def redis_dup(self) -> AsyncMock:
        """Redis client where SET NX fails → duplicate lead."""
        r = AsyncMock()
        r.set = AsyncMock(return_value=None)
        return r

    @pytest.mark.asyncio
    async def test_duplicate_skips_db_write(self, redis_dup: AsyncMock):
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("core_app.worker.async_session_factory", return_value=mock_ctx) as mock_factory:
            await _process_lead(redis_dup, _raw_lead())

        mock_factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_does_not_commit(self, redis_dup: AsyncMock):
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("core_app.worker.async_session_factory", return_value=mock_ctx):
            await _process_lead(redis_dup, _raw_lead())

        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_redis_set_still_checked_for_duplicate(self, redis_dup: AsyncMock):
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("core_app.worker.async_session_factory", return_value=mock_ctx):
            await _process_lead(redis_dup, _raw_lead())

        redis_dup.set.assert_awaited_once()
