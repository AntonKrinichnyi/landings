import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from landings_app.schemas import LeadCreateSchema
from landings_app.services import token_auth, get_redis, logger

router = APIRouter()


@router.post(
    "/lead",
    status_code=status.HTTP_200_OK,
    description="Submit a new lead from a landing page for processing. The lead is validated and queued for asynchronous persistence to the database.",
    responses={
        200: {
            "description": "Lead successfully queued for processing",
            "content": {
                "application/json": {
                    "example": {"status": "queued"}
                }
            }
        },
        400: {"description": "Invalid lead data (missing required fields or invalid format)"},
        401: {"description": "Missing or invalid authentication token"},
        403: {"description": "Affiliate ID in request body does not match the authenticated token"},
        422: {"description": "Validation error in lead data"},
    },
    tags=["Leads"],
)
async def create_lead(
    lead: LeadCreateSchema,
    affiliate_id: UUID = Depends(token_auth),
    redis=Depends(get_redis),
):
    """Create and queue a new lead for processing.
    
    Validates that the affiliate ID in the request body matches the
    authenticated token, then pushes the lead data to the Redis queue
    for asynchronous processing.
    
    Args:
        lead: Lead data containing name, phone, country, offer_id, and affiliate_id.
        affiliate_id: UUID of authenticated affiliate (from token).
        redis: Redis async client for queue operations.
        
    Returns:
        dict: Status confirmation with "queued" message.
        
    Raises:
        HTTPException: If affiliate_id in body does not match authenticated
            token (status 403).
    """
    logger.info("POST /lead requested by affiliate: %s (offer_id=%s)", affiliate_id, lead.offer_id)
    if lead.affiliate_id != affiliate_id:
        logger.warning("Forbidden: affiliate_id mismatch - token=%s, body=%s", affiliate_id, lead.affiliate_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="affiliate_id in body does not match the authenticated token",
        )

    payload = lead.model_dump(mode="json")
    await redis.lpush("leads:queue", json.dumps(payload))
    logger.info("Lead queued successfully: name=%s, phone=%s", lead.name, lead.phone)

    return {"status": "queued"}
