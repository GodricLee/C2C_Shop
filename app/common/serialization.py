"""Helpers for making data JSON serializable."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Sequence


def _to_serializable(value: Any) -> Any:
    """Best-effort conversion of nested values into JSON-safe primitives."""

    if isinstance(value, Mapping):
        return {str(key): _to_serializable(val) for key, val in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_to_serializable(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def serialize_diff(diff: Any) -> Any:
    """Return a deep-copied structure containing only JSON-safe primitives."""

    return _to_serializable(diff)
