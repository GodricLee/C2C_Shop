"""Membership schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.membership import MembershipLevel
from app.schemas.common import APIModel


class MembershipUpgradeRequest(BaseModel):
    level: MembershipLevel
    duration_days: int = 365


class MembershipOut(APIModel):
    user_id: int
    level: MembershipLevel
    expires_at: Optional[datetime]
    created_at: datetime
