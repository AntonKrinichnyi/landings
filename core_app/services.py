from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose.exceptions import JWTError
from jose import jwt

from core_app.config import settings
from core_app.worker import logger


_token_auth_scheme = HTTPBearer()

async def get_redis(request: Request):
    """Retrieve Redis client from application state.
    
    Args:
        request: FastAPI request object.
        
    Returns:
        Redis async client instance.
    """
    return request.app.state.redis

async def token_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_token_auth_scheme),
) -> UUID:
    """Validate JWT token and extract affiliate ID.
    
    Decodes and validates the JWT token from the Authorization header,
    extracts the affiliate ID claim, and returns it as a UUID.
    
    Args:
        credentials: HTTP Bearer token credentials.
        
    Returns:
        UUID: The affiliate ID extracted from the token.
        
    Raises:
        HTTPException: If token is invalid, missing required claims, or
            fails JWT validation (status 401).
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )

        raw_id = payload.get("id")

        if raw_id is None:
            logger.warning("Token validation failed: missing 'id' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing 'id' claim in token",
            )
        affiliate_id = UUID(str(raw_id))
        logger.info("Token validated successfully for affiliate: %s", affiliate_id)
        return affiliate_id

    except (JWTError, ValueError) as e:
        logger.warning("Token validation failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from e
