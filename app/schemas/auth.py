"""Authentication specific schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import TwoFAMethodType
from app.schemas.common import APIModel
from app.schemas.user import SessionOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_info: Optional[str] = None
    ip_address: Optional[str] = None


class LoginFlowResponse(APIModel):
    flow_id: str
    channel: TwoFAMethodType
    expires_at: datetime


class Verify2FARequest(BaseModel):
    flow_id: str
    code: str = Field(min_length=6, max_length=6)


class TokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"
    session: SessionOut


class LogoutRequest(BaseModel):
    session_id: int
