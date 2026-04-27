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


@router.get(
    "/leads",
    response_model=list[DateGroupSchema | OfferGroupSchema],
    description="Retrieve leads for the authenticated affiliate within a specified date range. Results can be grouped by date or offer.",
    responses={
        200: {
            "description": "Leads successfully retrieved and grouped",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "date": "2024-01-15",
                            "count": 3,
                            "leads": [
                                {
                                    "id": "550e8400-e29b-41d4-a716-446655440000",
                                    "name": "John Doe",
                                    "phone": "+1234567890",
                                    "country": "US",
                                    "offer_id": "550e8400-e29b-41d4-a716-446655440001",
                                    "affiliate_id": "550e8400-e29b-41d4-a716-446655440002",
                                    "created_at": "2024-01-15T10:30:00"
                                }
                            ]
                        }
                    ]
                }
            }
        },
        400: {"description": "Invalid query parameters (e.g., invalid date format or group value)"},
        401: {"description": "Missing or invalid authentication token"},
        422: {"description": "Validation error in request parameters"},
    },
    tags=["Leads"],
)
async def get_leads(
    date_from: date = Query(..., description="Start date for filtering leads (format: YYYY-MM-DD)"),
    date_to: date = Query(..., description="End date for filtering leads (format: YYYY-MM-DD)"),
    date_group: GroupBy = Query(..., alias="group", description="Grouping criteria: 'date' to group by creation date or 'offer' to group by offer ID"),
    affiliate_id: UUID = Depends(token_auth),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve leads for an affiliate filtered by date range.
    
    Fetches leads created by the authenticated affiliate within the specified
    date range and groups them by either date or offer based on the request.
    
    Args:
        date_from: Start date for filtering leads (inclusive).
        date_to: End date for filtering leads (inclusive).
        date_group: Grouping criteria - 'date' to group by date,
            'offer' to group by offer.
        affiliate_id: UUID of authenticated affiliate (from token).
        db: Async database session.
        
    Returns:
        List of DateGroupSchema or OfferGroupSchema objects containing
            grouped lead data with counts and details.
    """
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
