from fastapi import FastAPI

from landings_app.routers import router

app = FastAPI(title="Landings API")

app.include_router(router)
