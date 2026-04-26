import uuid

import pytest
from pydantic import ValidationError

from landings_app.schemas import LeadCreateSchema


OFFER_ID = uuid.uuid4()
AFFILIATE_ID = uuid.uuid4()


def _base() -> dict:
    return {
        "name": "Alice",
        "phone": "+440000000000",
        "country": "GB",
        "offer_id": str(OFFER_ID),
        "affiliate_id": str(AFFILIATE_ID),
    }


class TestLeadCreateValid:
    def test_all_fields_accepted(self):
        lead = LeadCreateSchema(**_base())
        assert lead.name == "Alice"
        assert lead.country == "GB"
        assert lead.offer_id == OFFER_ID
        assert lead.affiliate_id == AFFILIATE_ID

    def test_country_two_uppercase_letters(self):
        for code in ("US", "DE", "PL", "JP"):
            lead = LeadCreateSchema(**{**_base(), "country": code})
            assert lead.country == code


class TestLeadCreateInvalidCountry:
    @pytest.mark.parametrize("bad_country", [
        "us",        # lowercase
        "Gb",        # mixed case
        "GBR",       # too long (alpha-3)
        "G",         # too short
        "12",        # digits
        "",          # empty
        "G B",       # space
    ])
    def test_invalid_country_raises(self, bad_country: str):
        with pytest.raises(ValidationError):
            LeadCreateSchema(**{**_base(), "country": bad_country})


class TestLeadCreateMissingFields:
    @pytest.mark.parametrize("field", ["name", "phone", "country", "offer_id", "affiliate_id"])
    def test_missing_required_field_raises(self, field: str):
        data = _base()
        del data[field]
        with pytest.raises(ValidationError):
            LeadCreateSchema(**data)

    def test_invalid_uuid_for_offer_id(self):
        with pytest.raises(ValidationError):
            LeadCreateSchema(**{**_base(), "offer_id": "not-a-uuid"})

    def test_invalid_uuid_for_affiliate_id(self):
        with pytest.raises(ValidationError):
            LeadCreateSchema(**{**_base(), "affiliate_id": "not-a-uuid"})
