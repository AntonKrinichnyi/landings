import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis import asyncio as async_redis

from core_app.routers import router
from core_app.config import settings
from core_app.db.connection import engine
from core_app.worker import worker_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = async_redis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.redis = redis_client

    worker_task = asyncio.create_task(worker_loop(redis_client))

    yield

    worker_task.cancel()
    await asyncio.gather(worker_task, return_exceptions=True)
    await redis_client.aclose()
    await engine.dispose()

app = FastAPI(title="Core App", lifespan=lifespan)

app.include_router(router)
