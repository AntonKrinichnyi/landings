import asyncio
import json
import logging
import uuid
from datetime import datetime

import redis.asyncio as aioredis

from core_app.db.connection import async_session_factory
from core_app.models import Lead

logger = logging.getLogger(__name__)

QUEUE_KEY = "leads:queue"
DEDUP_TTL = 600  # 10 minutes window


def _dedup_key(name: str, phone: str, offer_id: str, affiliate_id: str) -> str:
    """Generate a deduplication key for a lead.
    
    Creates a unique key combining lead attributes to identify and prevent
    duplicate lead submissions within the TTL window.
    
    Args:
        name: Lead's full name.
        phone: Lead's phone number.
        offer_id: ID of the offer the lead is interested in.
        affiliate_id: ID of the affiliate who submitted the lead.
        
    Returns:
        str: Formatted deduplication key.
    """
    return f"dedup:{name}:{phone}:{offer_id}:{affiliate_id}"


async def _process_lead(redis_client: aioredis.Redis, raw: str) -> None:
    """Process and persist a lead from queue data.
    
    Parses JSON lead data from the queue, checks for duplicates using Redis
    with a TTL window, and persists new leads to the database.
    
    Args:
        redis_client: Redis async client for deduplication checks.
        raw: JSON string containing lead data.
        
    Returns:
        None
    """
    data = json.loads(raw)

    dedup_key = _dedup_key(
        data["name"],
        data["phone"],
        data["offer_id"],
        data["affiliate_id"],
    )
    is_new = await redis_client.set(dedup_key, 1, ex=DEDUP_TTL, nx=True)
    if not is_new:
        logger.info("Duplicate lead skipped: %s / %s", data["name"], data["phone"])
        return

    async with async_session_factory() as session:
        lead = Lead(
            name=data["name"],
            phone=data["phone"],
            country=data["country"],
            offer_id=uuid.UUID(data["offer_id"]),
            affiliate_id=uuid.UUID(data["affiliate_id"]),
            created_at=datetime.utcnow(),
        )
        session.add(lead)
        await session.commit()
        logger.info("Lead persisted: id=%s", lead.id)


async def worker_loop(redis_client: aioredis.Redis) -> None:
    logger.info("Worker started — listening on '%s'", QUEUE_KEY)
    while True:
        try:
            result = await redis_client.brpop(QUEUE_KEY, timeout=5)
            if result:
                _, raw = result
                await _process_lead(redis_client, raw)
        except asyncio.CancelledError:
            logger.info("Worker received cancellation — shutting down gracefully.")
            break
        except Exception:
            logger.exception("Unexpected error in worker loop — retrying in 1 s")
            await asyncio.sleep(1)
