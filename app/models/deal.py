"""Deal and transaction models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class DealStatus(str, Enum):
    """Deal lifecycle states."""

    INITIATED = "INITIATED"
    CONFIRMED_BY_SELLER = "CONFIRMED_BY_SELLER"
    CANCELED = "CANCELED"


class Deal(Base):
    """Represents a buyer-seller deal after contact exchange."""

    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[DealStatus] = mapped_column(
        SqlEnum(DealStatus), default=DealStatus.INITIATED, nullable=False
    )
    used_coupon_id: Mapped[Optional[int]] = mapped_column(ForeignKey("coupons.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    product: Mapped["Product"] = relationship("Product", back_populates="deals")
    buyer: Mapped["User"] = relationship(
        "User", foreign_keys=[buyer_id], back_populates="buyer_deals"
    )
    seller: Mapped["User"] = relationship(
        "User", foreign_keys=[seller_id], back_populates="seller_deals"
    )
    cashback: Mapped[Optional["Cashback"]] = relationship(
        back_populates="deal", uselist=False, cascade="all, delete-orphan"
    )
    coupon: Mapped[Optional["Coupon"]] = relationship("Coupon")
