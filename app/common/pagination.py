"""Utilities for paginating SQLAlchemy queries."""
from __future__ import annotations

from typing import Tuple

from fastapi import Query
from sqlalchemy import Select

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def pagination_params(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Items per page",
    ),
) -> Tuple[int, int]:
    """FastAPI dependency returning (page, page_size)."""

    return page, page_size


def apply_pagination(statement: Select, page: int, page_size: int) -> Select:
    """Apply offset/limit to a SQLAlchemy select statement."""

    offset = (page - 1) * page_size
    return statement.offset(offset).limit(page_size)
