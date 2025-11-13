"""Membership model definitions."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class MembershipLevel(str, Enum):
    """Membership tiers available to users."""

    NORMAL = "NORMAL"
    SHOPPER = "SHOPPER"


class Membership(Base):
    """Membership state for a user."""

    __tablename__ = "memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    level: Mapped[MembershipLevel] = mapped_column(
        SqlEnum(MembershipLevel), default=MembershipLevel.NORMAL, nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="membership")
