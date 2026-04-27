import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis import asyncio as async_redis

from core_app.routers import router
from core_app.config import settings
from core_app.db.connection import engine
from core_app.worker import worker_loop, logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage FastAPI application lifecycle events.
    
    Initializes Redis client and worker task on startup, and gracefully
    shuts down all resources on application termination.
    
    Args:
        app: FastAPI application instance.
        
    Yields:
        None
    """
    redis_client = async_redis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.redis = redis_client
    logger.info("Redis client connected")

    worker_task = asyncio.create_task(worker_loop(redis_client))
    logger.info("Worker task created")

    yield

    worker_task.cancel()
    await asyncio.gather(worker_task, return_exceptions=True)
    await redis_client.aclose()
    logger.info("Redis client closed")
    await engine.dispose()
    logger.info("Database engine disposed")

app = FastAPI(title="Core App", lifespan=lifespan)

app.include_router(router)
