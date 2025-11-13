"""Administrative configuration models."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AdminConfig(Base):
    """Singleton configuration row stored for platform parameters."""

    __tablename__ = "admin_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    cashback_default: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    current_parameter_set_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("parameter_sets.id"), nullable=True
    )

    current_parameter_set: Mapped[Optional["ParameterSet"]] = relationship(
        "ParameterSet",
        foreign_keys="AdminConfig.current_parameter_set_id",
        post_update=True,
    )
    parameter_sets: Mapped[list["ParameterSet"]] = relationship(
        "ParameterSet",
        back_populates="admin_config",
        foreign_keys="ParameterSet.admin_config_id",
        cascade="all, delete-orphan",
    )
