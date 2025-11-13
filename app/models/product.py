"""Product domain models."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base
from app.models.tag import product_tag_table


class ProductStatus(str, Enum):
    """Lifecycle states for a product listing."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    UNLISTED = "UNLISTED"
    SOLD = "SOLD"


class Product(Base):
    """Represents a product listed by a seller."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[ProductStatus] = mapped_column(
        SqlEnum(ProductStatus), default=ProductStatus.DRAFT, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    seller: Mapped["User"] = relationship(back_populates="products")
    tags: Mapped[List["Tag"]] = relationship(
        secondary=product_tag_table, back_populates="products"
    )
    deals: Mapped[List["Deal"]] = relationship(back_populates="product")