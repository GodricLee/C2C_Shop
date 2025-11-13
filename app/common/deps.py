"""Common FastAPI dependency helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.common.exceptions import AppError
from app.db import get_db
from app.models.user import Session as SessionModel
from app.models.user import User, UserStatus
from app.security.jwt import decode_access_token

security_scheme = HTTPBearer(auto_error=False)


def get_session(db: Session, session_id: int) -> SessionModel:
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session is None:
        raise AppError(401, "Session not found")
    return session


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the current user from the Authorization header."""

    if credentials is None:
        raise AppError(401, "Missing authorization header")
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = int(payload["sub"])
    session_id = int(payload["sid"])
    session = get_session(db, session_id=session_id)
    if session.revoked:
        raise AppError(401, "Session revoked")
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(tz=timezone.utc):
        raise AppError(401, "Session expired")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise AppError(401, "User not found")
    if user.status != UserStatus.ACTIVE:
        raise AppError(403, "User disabled")
    return user


def get_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Ensure the current user has administrator privileges."""

    _ = db  # reserved for future audit logging enrichment
    if not current_user.is_admin:
        raise AppError(403, "Administrator privileges required")
    return current_user