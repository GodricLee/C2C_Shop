"""Cashback records associated with deals."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class Cashback(Base):
    """Captures cashback generated after seller confirmation."""

    __tablename__ = "cashbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    ratio: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    deal: Mapped["Deal"] = relationship("Deal", back_populates="cashback")
