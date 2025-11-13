"""Tag moderation models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


product_tag_table = Table(
    "product_tags",
    Base.metadata,
    Column("product_id", ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class TagStatus(str, Enum):
    """Review workflow status of a tag."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MERGED = "MERGED"


class Tag(Base):
    """Seller-defined tag awaiting moderation."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[TagStatus] = mapped_column(
        SqlEnum(TagStatus), default=TagStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    products: Mapped[List["Product"]] = relationship(
        secondary=product_tag_table, back_populates="tags"
    )
    audits: Mapped[List["TagAudit"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )


class TagAudit(Base):
    """Audit trail for tag moderation decisions."""

    __tablename__ = "tag_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)
    actor_admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tag: Mapped["Tag"] = relationship(back_populates="audits")
    actor: Mapped["User"] = relationship("User")
