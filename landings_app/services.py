from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose.exceptions import JWTError
from jose import jwt

from landings_app.config import settings


_token_auth_scheme = HTTPBearer()


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
        return UUID(str(raw_id))

    except (JWTError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from e
