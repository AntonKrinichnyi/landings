import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from landings_app.schemas import LeadCreateSchema
from landings_app.services import token_auth, get_redis

router = APIRouter()


@router.post("/lead", status_code=status.HTTP_200_OK)
async def create_lead(
    lead: LeadCreateSchema,
    affiliate_id: UUID = Depends(token_auth),
    redis=Depends(get_redis),
):
    if lead.affiliate_id != affiliate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="affiliate_id in body does not match the authenticated token",
        )

    payload = lead.model_dump(mode="json")
    await redis.lpush("leads:queue", json.dumps(payload))

    return {"status": "queued"}
