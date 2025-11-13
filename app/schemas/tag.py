"""Tag schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.tag import TagStatus
from app.schemas.common import APIModel


class TagCreate(BaseModel):
    name: str


class TagOut(APIModel):
    id: int
    name: str
    status: TagStatus
    created_at: datetime
    updated_at: datetime


class TagModerationRequest(BaseModel):
    reason: Optional[str] = None
    merge_to_tag_id: Optional[int] = None


class TagAssignRequest(BaseModel):
    names: list[str]
