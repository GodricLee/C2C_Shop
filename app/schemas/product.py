"""Product schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.product import ProductStatus
from app.schemas.common import APIModel
from app.schemas.tag import TagOut


class ProductBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., gt=Decimal("0"))


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=Decimal("0"))
    status: Optional[ProductStatus] = None


class ProductOut(APIModel):
    id: int
    seller_id: int
    title: str
    description: Optional[str]
    price: Decimal
    status: ProductStatus
    created_at: datetime
    updated_at: datetime
    tags: List[TagOut] = Field(default_factory=list)


class ProductListResponse(APIModel):
    items: List[ProductOut]
    total: int
