import uuid
from datetime import datetime

import pytest

from core_app.schemas import LeadResponseSchema


AFFILIATE_ID = uuid.uuid4()
OFFER_ID = uuid.uuid4()
LEAD_ID = uuid.uuid4()

_CREATED_AT = datetime(2026, 4, 24, 12, 0, 0)


def _test_chema() -> dict:
    return {
        "id": LEAD_ID,
        "name": "Vasily",
        "phone": "+380507777777",
        "country": "UA",
        "offer_id": OFFER_ID,
        "affiliate_id": AFFILIATE_ID,
        "created_at": _CREATED_AT,
    }


class TestLeadResponseSchema:
    def test_lead_response_schema(self):
        data = _test_chema()
        lead_response = LeadResponseSchema(**data)
        assert lead_response.id == LEAD_ID
        assert lead_response.name == "Vasily"
        assert lead_response.phone == "+380507777777"
        assert lead_response.country == "UA"
        assert lead_response.offer_id == OFFER_ID
        assert lead_response.affiliate_id == AFFILIATE_ID
        assert lead_response.created_at == _CREATED_AT
    
    def test_lead_response_schema_invalid_data(self):
        data = _test_chema()
        data["phone"] = 380507777777
        with pytest.raises(ValueError):
            LeadResponseSchema(**data)
    
    def test_lead_response_schema_missing_field(self):
        data = _test_chema()
        del data["name"]
        with pytest.raises(ValueError):
            LeadResponseSchema(**data)
