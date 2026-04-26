import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from core_app.db.connection import Base


class Affiliate(Base):
    __tablename__ = "affiliates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    leads: Mapped[list["Lead"]] = relationship(back_populates="affiliate")


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    leads: Mapped[list["Lead"]] = relationship(back_populates="offer")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.now(timezone.utc))

    affiliate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("affiliates.id"), nullable=False)
    offer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("offers.id"), nullable=False)

    affiliate: Mapped["Affiliate"] = relationship(back_populates="leads")
    offer: Mapped["Offer"] = relationship(back_populates="leads")


class GroupBy(str, enum.Enum):
    date = "date"
    offer = "offer"
