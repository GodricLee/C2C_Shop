"""Coupon schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.models.coupon import CouponScope, CouponStatus
from app.schemas.common import APIModel


class CouponCreate(BaseModel):
    code: str = Field(..., max_length=64)
    status: CouponStatus = CouponStatus.DRAFT
    scope: CouponScope = CouponScope.ALL
    min_revenue: Decimal = Field(..., ge=Decimal("0"))
    min_sales: int = Field(..., ge=0)
    discount_amount: Decimal = Field(..., ge=Decimal("0"))
    description: Optional[str] = None
    expires_at: Optional[datetime] = None


class CouponUpdate(BaseModel):
    status: Optional[CouponStatus] = None
    min_revenue: Optional[Decimal] = Field(None, ge=Decimal("0"))
    min_sales: Optional[int] = Field(None, ge=0)
    discount_amount: Optional[Decimal] = Field(None, ge=Decimal("0"))
    description: Optional[str] = None
    expires_at: Optional[datetime] = None


class CouponOut(APIModel):
    id: int
    code: str
    status: CouponStatus
    scope: CouponScope
    min_revenue: Decimal
    min_sales: int
    discount_amount: Decimal
    description: Optional[str]
    expires_at: Optional[datetime]
    created_at: datetime


class CouponAssignRequest(BaseModel):
    user_id: int
