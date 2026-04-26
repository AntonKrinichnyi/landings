from uuid import UUID

from pydantic import BaseModel, Field

class LeadCreateSchema(BaseModel):
    name: str
    phone: str = Field(..., min_length=7, max_length=15, pattern=r"^\+?[1-9]\d{1,14}$")
    country: str = Field(..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    offer_id: UUID
    affiliate_id: UUID
