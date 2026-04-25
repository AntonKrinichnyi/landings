import uuid
from datetime import datetime

from pydantic import BaseModel

class LeadResponseSchema(BaseModel):
    id: uuid
    name: str
    phone: str
    country: str
    offer_id: uuid
    affiliate_id: uuid
    created_at: datetime

class OfferGroupSchema(BaseModel):
    id: uuid
    name: str
    leads: list[LeadResponseSchema]
