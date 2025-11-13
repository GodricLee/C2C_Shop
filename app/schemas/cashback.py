"""Cashback schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.schemas.common import APIModel


class CashbackOut(APIModel):
    id: int
    deal_id: int
    ratio: Decimal
    amount: Decimal
    created_at: datetime
