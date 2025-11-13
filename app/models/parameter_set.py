"""Parameter set models for versioned admin controls."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class ParameterStatus(str, Enum):
    """State of an admin parameter set."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class ParameterSet(Base):
    """Versioned collection of configuration values."""

    __tablename__ = "parameter_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_config_id: Mapped[int] = mapped_column(
        ForeignKey("admin_config.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ParameterStatus] = mapped_column(
        SqlEnum(ParameterStatus), default=ParameterStatus.DRAFT, nullable=False
    )
    effective_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    previous_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("parameter_sets.id", ondelete="SET NULL")
    )

    admin_config: Mapped["AdminConfig"] = relationship(
        "AdminConfig",
        back_populates="parameter_sets",
        foreign_keys="ParameterSet.admin_config_id",
    )
    previous_version: Mapped[Optional["ParameterSet"]] = relationship(
        "ParameterSet", remote_side="ParameterSet.id", back_populates="next_versions"
    )
    next_versions: Mapped[List["ParameterSet"]] = relationship(
        "ParameterSet", back_populates="previous_version", cascade="all, delete-orphan"
    )
    price_policy: Mapped[Optional["PricePolicy"]] = relationship(
        "PricePolicy", back_populates="parameter_set", uselist=False, cascade="all, delete-orphan"
    )


class PricePolicy(Base):
    """Platform-wide pricing guardrails."""

    __tablename__ = "price_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parameter_set_id: Mapped[int] = mapped_column(
        ForeignKey("parameter_sets.id", ondelete="CASCADE"), nullable=False
    )
    min_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subsidy_cap: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    parameter_set: Mapped["ParameterSet"] = relationship("ParameterSet", back_populates="price_policy")
