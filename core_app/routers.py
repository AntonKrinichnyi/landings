from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from core_app.connection import get_db

router = APIRouter()

@router.get("/leads")
async def get_leads(db: AsyncSession = Depends(get_db)):
    pass