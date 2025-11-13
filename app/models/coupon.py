"""Promotion related models."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class CouponStatus(str, Enum):
    """Lifecycle of a coupon."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    DISABLED = "DISABLED"


class CouponScope(str, Enum):
    """Defines coupon applicability."""

    ALL = "ALL"
    PRODUCT = "PRODUCT"


class Coupon(Base):
    """Discount coupon with dual thresholds."""

    __tablename__ = "coupons"
    __table_args__ = (UniqueConstraint("code", name="uq_coupons_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[CouponStatus] = mapped_column(
        SqlEnum(CouponStatus), default=CouponStatus.DRAFT, nullable=False
    )
    scope: Mapped[CouponScope] = mapped_column(
        SqlEnum(CouponScope), default=CouponScope.ALL, nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    min_revenue: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    min_sales: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    assignments: Mapped[List["CouponAssignment"]] = relationship(
        back_populates="coupon", cascade="all, delete-orphan"
    )


class CouponAssignment(Base):
    """Association between coupon and user."""

    __tablename__ = "coupon_assignments"
    __table_args__ = (UniqueConstraint("user_id", "coupon_id", name="uq_coupon_assignment"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="coupon_assignments")
    coupon: Mapped["Coupon"] = relationship(back_populates="assignments")
