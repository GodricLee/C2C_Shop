"""Common schema primitives."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class APIModel(BaseModel):
    """Base Pydantic model with ORM support."""

    class Config:
        orm_mode = True


class PaginationMeta(APIModel):
    page: int
    page_size: int
    total: int


class AuditInfo(APIModel):
    actor_user_id: Optional[int]
    action: str
    entity: str
    entity_id: str
    diff: Dict[str, Any]
    created_at: datetime


class Message(APIModel):
    message: str
