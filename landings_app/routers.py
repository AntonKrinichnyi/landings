import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from landings_app.schemas import LeadCreateSchema
from landings_app.services import token_auth, get_redis, logger

router = APIRouter()


@router.post("/lead", status_code=status.HTTP_200_OK)
async def create_lead(
    lead: LeadCreateSchema,
    affiliate_id: UUID = Depends(token_auth),
    redis=Depends(get_redis),
):
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
