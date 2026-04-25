from fastapi import APIRouter

router = APIRouter()

@router.get("/leads")
async def get_leads():
    pass