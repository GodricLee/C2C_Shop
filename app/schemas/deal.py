"""Deal schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.deal import DealStatus
from app.schemas.common import APIModel
from app.schemas.cashback import CashbackOut


class DealCreate(BaseModel):
    product_id: int


class DealConfirmRequest(BaseModel):
    coupon_id: Optional[int] = None


class DealOut(APIModel):
    id: int
    product_id: int
    buyer_id: int
    seller_id: int
    status: DealStatus
    used_coupon_id: Optional[int]
    created_at: datetime
    confirmed_at: Optional[datetime]
    cashback: Optional[CashbackOut]
