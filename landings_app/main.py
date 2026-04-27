from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis import asyncio as sync_redis

from landings_app.routers import router
from landings_app.config import settings
from landings_app.services import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Landings App initialization")
    app.state.redis = sync_redis.from_url(settings.REDIS_URL, decode_responses=True)
    logger.info("Redis client connected")
    yield
    logger.info("Shutting down Landings App")
    await app.state.redis.aclose()
    logger.info("Redis client closed")

app = FastAPI(title="Landings API", lifespan=lifespan)

app.include_router(router)
