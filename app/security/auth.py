"""Authentication helpers for login and 2FA workflows."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from app.common.exceptions import AppError
from app.config import get_settings
from app.models.user import Session as SessionModel
from app.models.user import TwoFAMethodType, User, UserStatus
from app.security.hashing import verify_password
from app.security.jwt import create_access_token
from app.security.twofa_transport import transport


uvicorn_logger = logging.getLogger("uvicorn.error")


@dataclass(slots=True)
class LoginFlow:
    """Represents an in-progress 2FA verification flow."""

    flow_id: str
    user_id: int
    channel: TwoFAMethodType
    code: str
    expires_at: datetime
    device_info: Optional[str]
    ip_address: Optional[str]
    debug_code: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        return datetime.now(tz=timezone.utc) >= self.expires_at


_flows: Dict[str, LoginFlow] = {}


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Validate a user's credentials."""

    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(401, "Invalid email or password")
    if user.status != UserStatus.ACTIVE:
        raise AppError(403, "Account disabled")
    return user


def initiate_login_flow(
    user: User,
    channel: TwoFAMethodType | None = None,
    device_info: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> LoginFlow:
    """Issue a 2FA code and store a pending flow for verification."""

    settings = get_settings()
    available_channels = {
        TwoFAMethodType[name]
        for name in (ch.strip().upper() for ch in settings.twofa_channels)
        if name in TwoFAMethodType.__members__
    }
    if not available_channels:
        raise AppError(500, "No valid 2FA channels configured")
    chosen_channel = channel or next(iter(available_channels))
    if chosen_channel not in available_channels:
        raise AppError(400, "Requested 2FA channel not enabled")

    code = transport.send_code(user_id=user.id, channel=chosen_channel)
    expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=5)
    debug_code = None
    if settings.app_env != "prod":  # expose code only in non-production environments
        debug_code = code
        uvicorn_logger.info(
            "[2FA] env=%s user_id=%s channel=%s code=%s",
            settings.app_env,
            user.id,
            chosen_channel.value,
            debug_code,
        )
    flow = LoginFlow(
        flow_id=str(uuid4()),
        user_id=user.id,
        channel=chosen_channel,
        code=code,
        expires_at=expires_at,
        device_info=device_info,
        ip_address=ip_address,
        debug_code=debug_code,
    )
    _flows[flow.flow_id] = flow
    return flow


def complete_twofa(db: Session, flow_id: str, code: str) -> Tuple[str, SessionModel]:
    """Verify a 2FA code and create a session + JWT token."""

    flow = _flows.get(flow_id)
    if flow is None or flow.is_expired:
        raise AppError(400, "2FA flow expired or invalid")
    if not transport.verify_code(flow.user_id, flow.channel, code):
        raise AppError(401, "Invalid 2FA code")

    settings = get_settings()
    expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=settings.jwt_exp_hours)

    session = SessionModel(
        user_id=flow.user_id,
        issued_at=datetime.now(tz=timezone.utc),
        expires_at=expires_at,
        device_info=flow.device_info,
        ip_address=flow.ip_address,
    )
    db.add(session)
    db.flush()  # to populate session.id

    token = create_access_token(subject=str(flow.user_id), session_id=session.id)
    del _flows[flow_id]
    return token, session


def revoke_session(db: Session, session_id: int) -> None:
    """Mark an existing session as revoked."""

    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session is None:
        raise AppError(404, "Session not found")
    session.revoked = True
    db.add(session)
