from uuid import UUID
from datetime import datetime, date

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query

from core_app.db.connection import get_db
from core_app.services import token_auth
from core_app.models import GroupBy, Lead
from core_app.schemas import LeadResponseSchema, DateGroupSchema, OfferGroupSchema
from core_app.worker import logger

router = APIRouter()


@router.get("/leads", response_model=list[DateGroupSchema | OfferGroupSchema])
async def get_leads(
    date_from: date = Query(..., description="Start date for filtering leads"),
    date_to: date = Query(..., description="End date for filtering leads"),
    date_group: GroupBy = Query(..., alias="group", description="Grouping criteria: 'date' or 'offer'"),
    affiliate_id: UUID = Depends(token_auth),
    db: AsyncSession = Depends(get_db),
):
    logger.info("GET /leads requested by affiliate: %s (date_from=%s, date_to=%s, group=%s)", affiliate_id, date_from, date_to, date_group)
    date_from_dt = datetime.combine(date_from, datetime.min.time())
    date_to_dt = datetime.combine(date_to, datetime.max.time())

    stmt = (
        select(Lead)
        .options(selectinload(Lead.offer))
        .where(Lead.affiliate_id == affiliate_id)
        .where(Lead.created_at >= date_from_dt)
        .where(Lead.created_at <= date_to_dt)
        .order_by(Lead.created_at)
    )
    result = await db.execute(stmt)
    leads = result.scalars().all()
    logger.info("Retrieved %d leads for affiliate: %s", len(leads), affiliate_id)

    if date_group == GroupBy.date:
        buckets: dict[str, list[Lead]] = {}
        for lead in leads:
            day = lead.created_at.date().isoformat()
            buckets.setdefault(day, []).append(lead)

        return [
            DateGroupSchema(
                date=day,
                count=len(items),
                leads=[LeadResponseSchema.model_validate(l) for l in items],
            )
            for day, items in sorted(buckets.items())
        ]
    
    buckets_offer: dict[UUID, list[Lead]] = {}
    for lead in leads:
        buckets_offer.setdefault(lead.offer_id, []).append(lead)

    return [
        OfferGroupSchema(
            id=offer_id,
            name=items[0].offer.name,
            count=len(items),
            leads=[LeadResponseSchema.model_validate(l) for l in items],
        )
        for offer_id, items in buckets_offer.items()
    ]
