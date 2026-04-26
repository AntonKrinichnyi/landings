from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose.exceptions import JWTError
from jose import jwt

from landings_app.config import settings


_token_auth_scheme = HTTPBearer()

async def get_redis(request: Request):
    return request.app.state.redis


async def token_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_token_auth_scheme),
) -> UUID:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )

        raw_id = payload.get("id")

        if raw_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing 'id' claim in token",
            )
        try:
            return UUID(str(raw_id))
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            ) from e

    except (JWTError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from e
