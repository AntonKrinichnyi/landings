from fastapi import APIRouter

router = APIRouter()


@router.post("/lead")
async def create_lead():
    return {"message": "Lead created successfully"}
