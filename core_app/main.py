from fastapi import FastAPI

from core_app.routers import router

app = FastAPI(title="Core App")

app.include_router(router)
