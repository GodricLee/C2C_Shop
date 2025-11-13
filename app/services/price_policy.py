"""Helpers for retrieving price policy information."""
from __future__ import annotations

from decimal import Decimal
from typing import Tuple

from sqlalchemy.orm import Session

from app.common.exceptions import AppError
from app.models.admin_config import AdminConfig
from app.models.parameter_set import PricePolicy


def get_active_price_policy(db: Session) -> Tuple[Decimal, Decimal]:
    """Return the active min_price and subsidy_cap values."""

    config = db.query(AdminConfig).first()
    if config is None or config.current_parameter_set is None:
        raise AppError(500, "Admin configuration not initialized")

    price_policy: PricePolicy | None = config.current_parameter_set.price_policy
    if price_policy is None:
        raise AppError(500, "Price policy not set for active parameter")

    return price_policy.min_price, price_policy.subsidy_cap
