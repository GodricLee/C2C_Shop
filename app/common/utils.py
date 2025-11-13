"""Miscellaneous utility helpers."""
from __future__ import annotations

from decimal import Decimal


def decimal_to_float(value: Decimal | None) -> float | None:
    """Convert Decimal values to float for JSON responses."""

    if value is None:
        return None
    return float(value)
def ensure_bool(value: Any) -> bool:
