"""User related schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import TwoFAMethodType, UserStatus
from app.schemas.common import APIModel


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserOut(APIModel):
    id: int
    email: EmailStr
    is_admin: bool
    two_fa_enabled: bool
    status: UserStatus
    created_at: datetime


class SessionOut(APIModel):
    id: int
    issued_at: datetime
    expires_at: datetime
    device_info: Optional[str]
    ip_address: Optional[str]


class TwoFAMethodOut(APIModel):
    type: TwoFAMethodType
    enabled: bool
