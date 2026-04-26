import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from landings_app.services import token_auth

JWT_SECRET = "unit-test-secret"
JWT_ALGORITHM = "HS256"
AFFILIATE_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _make_creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _token(payload: dict, secret: str = JWT_SECRET) -> str:
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


@pytest.fixture(autouse=True)
def patch_settings():
    with patch("landings_app.services.settings") as mock_settings:
        mock_settings.JWT_SECRET = JWT_SECRET
        mock_settings.JWT_ALGORITHM = JWT_ALGORITHM
        yield


class TestVerifyJwtValid:
    @pytest.mark.asyncio
    async def test_returns_affiliate_uuid(self):
        token = _token({"id": str(AFFILIATE_ID)})
        result = await token_auth(_make_creds(token))
        assert result == AFFILIATE_ID

    @pytest.mark.asyncio
    async def test_uuid_type_returned(self):
        token = _token({"id": str(AFFILIATE_ID)})
        result = await token_auth(_make_creds(token))
        assert isinstance(result, uuid.UUID)


class TestVerifyJwtInvalid:
    @pytest.mark.asyncio
    async def test_missing_id_claim_raises_401(self):
        token = _token({"sub": "someone"})
        with pytest.raises(HTTPException) as exc_info:
            await token_auth(_make_creds(token))
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing 'id' claim in token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_uuid_in_id_claim_raises_401(self):
        token = _token({"id": "not-a-uuid"})
        with pytest.raises(HTTPException) as exc_info:
            await token_auth(_make_creds(token))
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_wrong_secret_raises_401(self):
        token = _token({"id": str(AFFILIATE_ID)}, secret="wrong-secret")
        with pytest.raises(HTTPException) as exc_info:
            await token_auth(_make_creds(token))
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_malformed_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            await token_auth(_make_creds("not.a.jwt"))
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_invalid_uuid_in_id_claim_raises_401(self):
        token = _token({"id": "not-a-uuid"})
        with pytest.raises(HTTPException) as exc_info:
            await token_auth(_make_creds(token))
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
