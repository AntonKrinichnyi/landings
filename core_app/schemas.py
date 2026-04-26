import uuid
from datetime import datetime

from pydantic import BaseModel

class LeadResponseSchema(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    country: str
    offer_id: uuid.UUID
    affiliate_id: uuid.UUID
    created_at: datetime


class DateGroupSchema(BaseModel):
    date: str
    count: int
    leads: list[LeadResponseSchema]


class OfferGroupSchema(BaseModel):
    id: uuid.UUID
    name: str
    count: int
    leads: list[LeadResponseSchema]
