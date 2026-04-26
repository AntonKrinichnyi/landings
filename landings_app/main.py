from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis import asyncio as sync_redis

from landings_app.routers import router
from landings_app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = sync_redis.from_url(settings.REDIS_URL, decode_responses=True)
    yield
    await app.state.redis.aclose()

app = FastAPI(title="Landings API", lifespan=lifespan)

app.include_router(router)
